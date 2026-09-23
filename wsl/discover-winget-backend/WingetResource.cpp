#include "WingetResource.h"
#include "WingetClient.h"

#include <QDesktopServices>
#include <QIcon>
#include <QProcess>
#include <QUrl>
#include <QDebug>

WingetResource::WingetResource(const QString &id,
                               const QString &name,
                               AbstractResourcesBackend *parent)
    : AbstractResource(parent)
    , m_id(id)
    , m_name(name.isEmpty() ? id : name)
    , m_iconName(QStringLiteral("package-x-generic"))
{
    // Derive initial category hints
    QString lower = (m_id + u' ' + m_name).toLower();
    if (lower.contains(QLatin1String("browser")) || lower.contains(QLatin1String("firefox")) ||
        lower.contains(QLatin1String("chrome")) || lower.contains(QLatin1String("edge")) ||
        lower.contains(QLatin1String("web"))) {
        m_categories << QStringLiteral("Network");
    }
    if (lower.contains(QLatin1String("code")) || lower.contains(QLatin1String("studio")) ||
        lower.contains(QLatin1String("dev")) || lower.contains(QLatin1String("git")) ||
        lower.contains(QLatin1String("python")) || lower.contains(QLatin1String("jetbrains"))) {
        m_categories << QStringLiteral("Development");
    }
    if (lower.contains(QLatin1String("media")) || lower.contains(QLatin1String("video")) ||
        lower.contains(QLatin1String("audio")) || lower.contains(QLatin1String("vlc")) ||
        lower.contains(QLatin1String("spotify")) || lower.contains(QLatin1String("player"))) {
        m_categories << QStringLiteral("AudioVideo");
    }
    if (lower.contains(QLatin1String("gimp")) || lower.contains(QLatin1String("photo")) ||
        lower.contains(QLatin1String("paint")) || lower.contains(QLatin1String("graphics")) ||
        lower.contains(QLatin1String("blender")) || lower.contains(QLatin1String("draw"))) {
        m_categories << QStringLiteral("Graphics");
    }
    if (lower.contains(QLatin1String("office")) || lower.contains(QLatin1String("document")) ||
        lower.contains(QLatin1String("word")) || lower.contains(QLatin1String("excel")) ||
        lower.contains(QLatin1String("pdf")) || lower.contains(QLatin1String("mail"))) {
        m_categories << QStringLiteral("Office");
    }
    if (lower.contains(QLatin1String("game")) || lower.contains(QLatin1String("steam")) ||
        lower.contains(QLatin1String("epic")) || lower.contains(QLatin1String("play"))) {
        m_categories << QStringLiteral("Game");
    }
    if (lower.contains(QLatin1String("terminal")) || lower.contains(QLatin1String("powershell")) ||
        lower.contains(QLatin1String("system")) || lower.contains(QLatin1String("monitor"))) {
        m_categories << QStringLiteral("System");
    }
    if (m_categories.isEmpty()) {
        m_categories << QStringLiteral("Utility");
    }
}

QString WingetResource::packageName() const
{
    return m_id;
}

QString WingetResource::name() const
{
    return m_name;
}

QString WingetResource::comment()
{
    if (m_comment.isEmpty() && !m_description.isEmpty()) {
        return m_description.split(u'\n').first();
    }
    return m_comment.isEmpty() ? QStringLiteral("Windows package (winget)") : m_comment;
}

QString WingetResource::longDescription()
{
    if (!m_detailsFetched && m_description.isEmpty()) {
        const_cast<WingetResource *>(this)->fetchDetails();
    }
    return m_description.isEmpty() ? comment() : m_description;
}

QVariant WingetResource::icon() const
{
    if (m_iconName.startsWith(u'/')) {
        return QIcon(m_iconName);
    }
    return m_iconName;
}

bool WingetResource::canExecute() const
{
    return m_state == AbstractResource::Installed;
}

void WingetResource::invokeApplication() const
{
    // Invoke Windows application via cmd.exe start
    qDebug() << "[WingetResource] Invoking application:" << m_name;
    QProcess::startDetached(QStringLiteral("cmd.exe"), {QStringLiteral("/c"), QStringLiteral("start"), QStringLiteral("\"\""), m_name});
}

AbstractResource::State WingetResource::state()
{
    return m_state;
}

void WingetResource::setState(AbstractResource::State s)
{
    if (m_state != s) {
        m_state = s;
        Q_EMIT stateChanged();
    }
}

bool WingetResource::hasCategory(const QString &category) const
{
    if (category.isEmpty() || category == QLatin1String("All") ||
        category == QLatin1String("all") || category == QLatin1String("All Applications")) {
        return true;
    }
    for (const QString &cat : m_categories) {
        if (cat.compare(category, Qt::CaseInsensitive) == 0) {
            return true;
        }
    }
    return false;
}

AbstractResource::Type WingetResource::type() const
{
    return AbstractResource::Application;
}

quint64 WingetResource::size()
{
    return m_size;
}

QJsonArray WingetResource::licenses()
{
    QJsonArray arr;
    if (!m_license.isEmpty()) {
        QJsonObject licObj;
        licObj[QStringLiteral("name")] = m_license;
        arr.append(licObj);
    }
    return arr;
}

QString WingetResource::installedVersion() const
{
    return m_installedVersion;
}

QString WingetResource::availableVersion() const
{
    return m_version.isEmpty() ? m_installedVersion : m_version;
}

QString WingetResource::origin() const
{
    return QStringLiteral("winget");
}

QString WingetResource::section()
{
    return m_categories.isEmpty() ? QStringLiteral("Utility") : m_categories.first();
}

QString WingetResource::author() const
{
    return m_author.isEmpty() ? QStringLiteral("Windows Package") : m_author;
}

QList<PackageState> WingetResource::addonsInformation()
{
    return {};
}

QString WingetResource::sourceIcon() const
{
    return QStringLiteral("application-x-ms-dos-executable");
}

QDate WingetResource::releaseDate() const
{
    return {};
}

void WingetResource::fetchChangelog()
{
}

QUrl WingetResource::url() const
{
    if (m_homepage.isEmpty()) {
        return QUrl(QStringLiteral("https://github.com/microsoft/winget-pkgs"));
    }
    return QUrl(m_homepage);
}

QUrl WingetResource::homepage()
{
    return url();
}

void WingetResource::setInstalledVersion(const QString &ver)
{
    m_installedVersion = ver;
}

void WingetResource::setAvailableVersion(const QString &ver)
{
    m_version = ver;
}

void WingetResource::setComment(const QString &comment)
{
    m_comment = comment;
}

void WingetResource::setIconName(const QString &icon)
{
    if (!icon.isEmpty()) {
        m_iconName = icon;
    }
}

void WingetResource::setAuthor(const QString &author)
{
    m_author = author;
}

void WingetResource::updateFromDetails(const QJsonObject &details)
{
    m_detailsFetched = true;
    if (details.contains(QStringLiteral("description"))) {
        m_description = details.value(QStringLiteral("description")).toString();
    }
    if (details.contains(QStringLiteral("publisher"))) {
        m_author = details.value(QStringLiteral("publisher")).toString();
    }
    if (details.contains(QStringLiteral("homepage"))) {
        m_homepage = details.value(QStringLiteral("homepage")).toString();
    }
    if (details.contains(QStringLiteral("license"))) {
        m_license = details.value(QStringLiteral("license")).toString();
    }
    if (details.contains(QStringLiteral("version")) && m_version.isEmpty()) {
        m_version = details.value(QStringLiteral("version")).toString();
    }
    if (details.contains(QStringLiteral("icon"))) {
        setIconName(details.value(QStringLiteral("icon")).toString());
    }
}

void WingetResource::fetchDetails()
{
    if (m_detailsFetched) {
        return;
    }
    m_detailsFetched = true;
    QJsonObject details = WingetClient::show(m_id);
    if (!details.isEmpty()) {
        updateFromDetails(details);
    }
}
