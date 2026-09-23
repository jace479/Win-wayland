#include "WingetTransaction.h"
#include "WingetResource.h"
#include "WingetClient.h"
#include <resources/AbstractResourcesBackend.h>

#include <QThread>
#include <QTimer>
#include <QDebug>

WingetTransaction::WingetTransaction(WingetResource *app, Role role)
    : WingetTransaction(app, {}, role)
{
}

WingetTransaction::WingetTransaction(WingetResource *app, const AddonList &addons, Transaction::Role role)
    : Transaction(app->backend(), app, role, addons)
    , m_app(app)
{
    setCancellable(false);
    setStatus(DownloadingStatus);
    setProgress(10);

    QTimer::singleShot(50, this, &WingetTransaction::execute);
}

void WingetTransaction::execute()
{
    QString pkgId = m_app->packageName();
    Role currentRole = role();

    // Run winget execution in background thread
    QThread *thread = QThread::create([this, pkgId, currentRole]() {
        auto progressCb = [this](const QString &phase, int progress, const QString &message) {
            QMetaObject::invokeMethod(this, [this, phase, progress, message]() {
                if (phase == QLatin1String("downloading")) {
                    setStatus(DownloadingStatus);
                    setProgress(progress);
                } else if (phase == QLatin1String("installing")) {
                    setStatus(CommittingStatus);
                    setProgress(progress);
                } else if (phase == QLatin1String("done")) {
                    setProgress(100);
                }
            });
        };

        QJsonObject result;
        if (currentRole == InstallRole) {
            result = WingetClient::install(pkgId, progressCb);
        } else if (currentRole == RemoveRole) {
            result = WingetClient::uninstall(pkgId, progressCb);
        }

        bool ok = result.value(QStringLiteral("ok")).toBool();
        QString errorMsg = result.value(QStringLiteral("error")).toString();

        // Dispatch back to main thread
        QMetaObject::invokeMethod(this, [this, ok, errorMsg, currentRole]() {
            if (ok) {
                setProgress(100);
                if (currentRole == InstallRole) {
                    m_app->setState(AbstractResource::Installed);
                } else if (currentRole == RemoveRole) {
                    m_app->setState(AbstractResource::None);
                }
                setStatus(DoneStatus);
            } else {
                if (!errorMsg.isEmpty()) {
                    Q_EMIT passiveMessage(errorMsg);
                }
                setStatus(DoneWithErrorStatus);
            }
            deleteLater();
        });
    });

    connect(thread, &QThread::finished, thread, &QObject::deleteLater);
    thread->start();
}

void WingetTransaction::cancel()
{
    m_cancelled = true;
    setStatus(CancelledStatus);
}

void WingetTransaction::proceed()
{
}

#include "moc_WingetTransaction.cpp"
