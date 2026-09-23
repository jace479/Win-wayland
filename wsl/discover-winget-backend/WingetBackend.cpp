#include "WingetBackend.h"
#include "WingetResource.h"
#include "WingetTransaction.h"
#include "WingetSourcesBackend.h"
#include "WingetClient.h"

#include <resources/SourcesModel.h>
#include <resources/StandardBackendUpdater.h>
#include <Category/Category.h>

#include <KLocalizedString>
#include <KPluginFactory>
#include <QDebug>
#include <QThread>
#include <QTimer>

DISCOVER_BACKEND_PLUGIN(WingetBackend)

using namespace Qt::StringLiterals;

WingetBackend::WingetBackend(QObject *parent)
    : AbstractResourcesBackend(parent)
    , m_updater(new StandardBackendUpdater(this))
{
    connect(m_updater, &StandardBackendUpdater::updatesCountChanged, this, &WingetBackend::updatesCountChanged);

    // Register Winget source in Discover sources model
    SourcesModel::global()->addSourcesBackend(new WingetSourcesBackend(this));

    // Populate installed winget apps after Discover starts
    QTimer::singleShot(200, this, &WingetBackend::populateInstalled);
}

WingetBackend::~WingetBackend()
{
}

WingetResource *WingetBackend::resourceForPackage(const QString &id, const QString &name)
{
    QString key = id.toLower();
    if (m_resources.contains(key)) {
        return m_resources.value(key);
    }

    auto *res = new WingetResource(id, name, this);
    m_resources.insert(key, res);
    connect(res, &WingetResource::stateChanged, this, &WingetBackend::updatesCountChanged);
    return res;
}

void WingetBackend::populateInstalled()
{
    QThread *thread = QThread::create([this]() {
        QJsonArray pkgs = WingetClient::list();
        QMetaObject::invokeMethod(this, [this, pkgs]() {
            for (const QJsonValue &val : pkgs) {
                QJsonObject obj = val.toObject();
                QString id = obj.value(QStringLiteral("id")).toString();
                QString name = obj.value(QStringLiteral("name")).toString();
                QString version = obj.value(QStringLiteral("version")).toString();
                QString available = obj.value(QStringLiteral("available")).toString();
                QString icon = obj.value(QStringLiteral("icon")).toString();
                bool upgradable = obj.value(QStringLiteral("upgradable")).toBool();

                if (id.isEmpty()) {
                    continue;
                }

                WingetResource *res = resourceForPackage(id, name);
                res->setInstalledVersion(version);
                res->setAvailableVersion(available.isEmpty() ? version : available);
                res->setIconName(icon);
                res->setState(upgradable ? AbstractResource::Upgradeable : AbstractResource::Installed);
            }
            Q_EMIT contentsChanged();
            Q_EMIT updatesCountChanged();
        });
    });

    connect(thread, &QThread::finished, thread, &QObject::deleteLater);
    thread->start();
}

int WingetBackend::updatesCount() const
{
    int count = 0;
    for (WingetResource *res : m_resources) {
        if (res->state() == AbstractResource::Upgradeable) {
            count++;
        }
    }
    return count;
}

AbstractBackendUpdater *WingetBackend::backendUpdater() const
{
    return m_updater;
}

AbstractReviewsBackend *WingetBackend::reviewsBackend() const
{
    return nullptr;
}

ResultsStream *WingetBackend::search(const AbstractResourcesBackend::Filters &filter)
{
    if (!filter.resourceUrl.isEmpty()) {
        return findResourceByPackageName(filter.resourceUrl);
    }

    // If searching installed / upgradeable packages only
    if (filter.state == AbstractResource::Installed || filter.state == AbstractResource::Upgradeable) {
        QVector<StreamResult> list;
        for (WingetResource *r : std::as_const(m_resources)) {
            if (filter.state == AbstractResource::Upgradeable && r->state() != AbstractResource::Upgradeable) {
                continue;
            }
            if (filter.state == AbstractResource::Installed && r->state() < AbstractResource::Installed) {
                continue;
            }
            if (filter.category && !r->hasCategory(filter.category->name())) {
                continue;
            }
            if (!filter.search.isEmpty() && !r->name().contains(filter.search, Qt::CaseInsensitive) &&
                !r->packageName().contains(filter.search, Qt::CaseInsensitive)) {
                continue;
            }
            list.append(r);
        }
        return new ResultsStream(QStringLiteral("WingetInstalledStream"), list);
    }

    // Search query provided: query winget-proxy
    if (!filter.search.isEmpty()) {
        QJsonArray results = WingetClient::search(filter.search, 30);
        QVector<StreamResult> streamResults;
        for (const QJsonValue &val : results) {
            QJsonObject obj = val.toObject();
            QString id = obj.value(QStringLiteral("id")).toString();
            QString name = obj.value(QStringLiteral("name")).toString();
            QString version = obj.value(QStringLiteral("version")).toString();
            QString icon = obj.value(QStringLiteral("icon")).toString();

            if (id.isEmpty()) {
                continue;
            }

            WingetResource *res = resourceForPackage(id, name);
            res->setAvailableVersion(version);
            res->setIconName(icon);

            if (filter.category && !res->hasCategory(filter.category->name())) {
                continue;
            }

            streamResults.append(res);
        }
        return new ResultsStream(QStringLiteral("WingetSearchStream"), streamResults);
    }

    // Browsing without specific search query: return known resources
    QVector<StreamResult> generalResults;
    for (WingetResource *r : std::as_const(m_resources)) {
        if (filter.category && !r->hasCategory(filter.category->name())) {
            continue;
        }
        generalResults.append(r);
    }
    return new ResultsStream(QStringLiteral("WingetBrowseStream"), generalResults);
}

ResultsStream *WingetBackend::findResourceByPackageName(const QUrl &search)
{
    QString pkgName = search.scheme() == QLatin1String("winget") ? search.path() : search.toString();
    WingetResource *res = resourceForPackage(pkgName);
    return new ResultsStream(QStringLiteral("WingetResourceStream"), {res});
}

Transaction *WingetBackend::installApplication(AbstractResource *app, const AddonList &addons)
{
    Q_UNUSED(addons);
    return installApplication(app);
}

Transaction *WingetBackend::installApplication(AbstractResource *app)
{
    auto *res = qobject_cast<WingetResource *>(app);
    return new WingetTransaction(res, Transaction::InstallRole);
}

Transaction *WingetBackend::removeApplication(AbstractResource *app)
{
    auto *res = qobject_cast<WingetResource *>(app);
    return new WingetTransaction(res, Transaction::RemoveRole);
}

void WingetBackend::checkForUpdates()
{
    if (m_fetchingUpdates) {
        return;
    }
    m_fetchingUpdates = true;

    QThread *thread = QThread::create([this]() {
        QJsonArray upgrades = WingetClient::upgradable();
        QMetaObject::invokeMethod(this, [this, upgrades]() {
            onUpdatesFound(upgrades);
        });
    });

    connect(thread, &QThread::finished, thread, &QObject::deleteLater);
    thread->start();
}

void WingetBackend::onUpdatesFound(const QJsonArray &packages)
{
    for (const QJsonValue &val : packages) {
        QJsonObject obj = val.toObject();
        QString id = obj.value(QStringLiteral("id")).toString();
        QString name = obj.value(QStringLiteral("name")).toString();
        QString available = obj.value(QStringLiteral("available")).toString();

        if (id.isEmpty()) {
            continue;
        }

        WingetResource *res = resourceForPackage(id, name);
        res->setAvailableVersion(available);
        res->setState(AbstractResource::Upgradeable);
    }

    m_fetchingUpdates = false;
    Q_EMIT updatesCountChanged();
}

QString WingetBackend::displayName() const
{
    return QStringLiteral("Windows Package Manager (winget)");
}

bool WingetBackend::hasApplications() const
{
    return true;
}

bool WingetBackend::isValid() const
{
    return true;
}

int WingetBackend::fetchingUpdatesProgress() const
{
    return m_fetchingUpdates ? 50 : 100;
}

#include "WingetBackend.moc"
#include "moc_WingetBackend.cpp"
