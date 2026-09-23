#include "AppModel.hpp"
#include "UwpLauncher.hpp"
#include "IconUtils.hpp"
#include <shobjidl.h>
#include <QDirIterator>
#include <QFileInfo>
#include <QDebug>
#include <QCryptographicHash>
#include <QProcess>

namespace KWinWin::UI {

// ============================================================================
// AppIconProvider Implementation
// ============================================================================

AppIconProvider::AppIconProvider()
    : QQuickImageProvider(QQuickImageProvider::Image)
{
}

QImage AppIconProvider::requestImage(const QString& id, QSize* size, const QSize& requestedSize)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_icons.find(id.toStdString());
    if (it != m_icons.end() && !it->second.isNull()) {
        QImage result = it->second;
        if (size) *size = result.size();
        if (requestedSize.isValid() && requestedSize != result.size()) {
            result = result.scaled(requestedSize, Qt::KeepAspectRatio, Qt::SmoothTransformation);
        }
        return result;
    }

    if (size) *size = QSize(48, 48);
    QImage placeholder(48, 48, QImage::Format_ARGB32);
    placeholder.fill(QColor(61, 174, 233, 100)); // Breeze Blue Accent placeholder
    return placeholder;
}

void AppIconProvider::addIcon(const QString& id, const QImage& image)
{
    if (!image.isNull()) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_icons[id.toStdString()] = image;
    }
}

void AppIconProvider::clear()
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_icons.clear();
}

// ============================================================================
// AppModel Implementation
// ============================================================================

AppModel::AppModel(AppIconProvider* iconProvider, QObject* parent)
    : QAbstractListModel(parent)
    , m_iconProvider(iconProvider)
{
    m_categories = {
        "All Applications",
        "Development",
        "Games",
        "Graphics",
        "Internet",
        "Multimedia",
        "Office",
        "System",
        "Utilities",
        "Applications"
    };

    reloadApplications();
}

void AppModel::setCategoryFilter(const QString& filter)
{
    if (m_categoryFilter != filter) {
        m_categoryFilter = filter;
        emit categoryFilterChanged();
        updateFilter();
    }
}

void AppModel::setSearchFilter(const QString& filter)
{
    if (m_searchFilter != filter) {
        m_searchFilter = filter;
        emit searchFilterChanged();
        updateFilter();
    }
}

void AppModel::updateFilter()
{
    beginResetModel();
    m_filteredIndices.clear();

    QString query = m_searchFilter.trimmed().toLower();
    bool allCats = (m_categoryFilter.isEmpty() || m_categoryFilter == "All Applications");

    for (int i = 0; i < m_apps.size(); ++i) {
        const auto& app = m_apps[i];
        bool catMatch = allCats || (app.category.compare(m_categoryFilter, Qt::CaseInsensitive) == 0);
        bool searchMatch = query.isEmpty() ||
            app.name.toLower().contains(query) ||
            app.category.toLower().contains(query) ||
            app.execOrAumid.toLower().contains(query);

        if (catMatch && searchMatch) {
            m_filteredIndices.push_back(i);
        }
    }
    endResetModel();
    emit countChanged();
}

int AppModel::rowCount(const QModelIndex& parent) const
{
    if (parent.isValid()) return 0;
    return static_cast<int>(m_filteredIndices.size());
}

QVariant AppModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= static_cast<int>(m_filteredIndices.size())) {
        return {};
    }

    int actualIndex = m_filteredIndices[index.row()];
    if (actualIndex < 0 || actualIndex >= m_apps.size()) {
        return {};
    }

    const auto& app = m_apps.at(actualIndex);
    switch (role) {
    case IdRole:
        return app.id;
    case NameRole:
    case Qt::DisplayRole:
        return app.name;
    case ExecRole:
        return app.execOrAumid;
    case CategoryRole:
        return app.category;
    case IsUwpRole:
        return app.isUwp;
    case IconUrlRole:
        return QString("image://appicon/%1").arg(app.id);
    case SearchRole:
        return QString("%1 %2 %3").arg(app.name, app.category, app.execOrAumid).toLower();
    default:
        return {};
    }
}

QHash<int, QByteArray> AppModel::roleNames() const
{
    return {
        { IdRole, "appId" },
        { NameRole, "appName" },
        { ExecRole, "execPath" },
        { CategoryRole, "category" },
        { IsUwpRole, "isUwp" },
        { IconUrlRole, "iconUrl" },
        { SearchRole, "searchKey" }
    };
}

QImage AppModel::extractBinaryIcon(const QString& filePath, int iconIndex)
{
    if (filePath.isEmpty()) return {};

    std::wstring wPath = filePath.toStdWString();

    // 1. First try SHGetFileInfoW for shell-resolved icon (handles .lnk, .exe, system icons, associations)
    SHFILEINFO sfi{};
    DWORD_PTR hrSfi = SHGetFileInfoW(wPath.c_str(), 0, &sfi, sizeof(sfi), SHGFI_ICON | SHGFI_LARGEICON);
    if (hrSfi && sfi.hIcon) {
        QImage img = hiconToQImage(sfi.hIcon);
        DestroyIcon(sfi.hIcon);
        if (!img.isNull()) {
            return img;
        }
    }

    // 2. Try PrivateExtractIconsW
    HICON hIcon = nullptr;
    UINT iconId = 0;
    UINT extracted = PrivateExtractIconsW(
        wPath.c_str(),
        iconIndex,
        48, 48,
        &hIcon,
        &iconId,
        1,
        LR_LOADFROMFILE
    );

    if (extracted > 0 && hIcon) {
        QImage img = hiconToQImage(hIcon);
        DestroyIcon(hIcon);
        if (!img.isNull()) {
            return img;
        }
    }

    // 3. Fallback to ExtractIconExW
    hIcon = nullptr;
    if (ExtractIconExW(wPath.c_str(), iconIndex, &hIcon, nullptr, 1) > 0 && hIcon) {
        QImage img = hiconToQImage(hIcon);
        DestroyIcon(hIcon);
        if (!img.isNull()) {
            return img;
        }
    }

    // 4. Default executable icon fallback
    ZeroMemory(&sfi, sizeof(sfi));
    if (SHGetFileInfoW(L".exe", FILE_ATTRIBUTE_NORMAL, &sfi, sizeof(sfi), SHGFI_ICON | SHGFI_LARGEICON | SHGFI_USEFILEATTRIBUTES) && sfi.hIcon) {
        QImage img = hiconToQImage(sfi.hIcon);
        DestroyIcon(sfi.hIcon);
        return img;
    }

    return {};
}

bool AppModel::resolveShellLink(const QString& lnkPath, AppEntry& outEntry)
{
    IShellLinkW* psl = nullptr;
    HRESULT hr = CoCreateInstance(CLSID_ShellLink, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&psl));
    if (FAILED(hr) || !psl) {
        return false;
    }

    IPersistFile* ppf = nullptr;
    hr = psl->QueryInterface(IID_PPV_ARGS(&ppf));
    if (FAILED(hr) || !ppf) {
        psl->Release();
        return false;
    }

    std::wstring wLnk = lnkPath.toStdWString();
    hr = ppf->Load(wLnk.c_str(), STGM_READ);
    if (FAILED(hr)) {
        ppf->Release();
        psl->Release();
        return false;
    }

    wchar_t szTarget[MAX_PATH]{};
    WIN32_FIND_DATAW wfd{};
    psl->GetPath(szTarget, MAX_PATH, &wfd, SLGP_UNCPRIORITY);

    wchar_t szArgs[MAX_PATH]{};
    psl->GetArguments(szArgs, MAX_PATH);

    wchar_t szDir[MAX_PATH]{};
    psl->GetWorkingDirectory(szDir, MAX_PATH);

    wchar_t szIcon[MAX_PATH]{};
    int iconIdx = 0;
    psl->GetIconLocation(szIcon, MAX_PATH, &iconIdx);

    ppf->Release();
    psl->Release();

    QString target = QString::fromWCharArray(szTarget);
    if (target.isEmpty() || target.endsWith(".url", Qt::CaseInsensitive)) {
        return false;
    }

    QFileInfo fi(lnkPath);
    outEntry.name = fi.completeBaseName();
    outEntry.execOrAumid = target;
    outEntry.arguments = QString::fromWCharArray(szArgs);
    outEntry.workingDir = QString::fromWCharArray(szDir);
    outEntry.isUwp = false;

    // First attempt: resolve shortcut directly via Windows Shell
    outEntry.icon = extractBinaryIcon(lnkPath, 0);

    // Second attempt: resolve from explicit icon location or target executable
    if (outEntry.icon.isNull()) {
        QString iconPath = QString::fromWCharArray(szIcon);
        if (iconPath.isEmpty() || !QFile::exists(iconPath)) {
            iconPath = target;
        }
        outEntry.icon = extractBinaryIcon(iconPath, iconIdx);
    }

    return true;
}

void AppModel::crawlStartMenuDirectory(const QString& dirPath, const QString& parentCategory, int depth)
{
    if (dirPath.isEmpty() || depth > 2) return;
    QDir dir(dirPath);
    if (!dir.exists()) return;

    QDir::Filters filters = QDir::Files | QDir::NoDotAndDotDot;
    if (depth < 2) {
        filters |= QDir::Dirs;
    }

    QFileInfoList entries = dir.entryInfoList(filters);
    for (const auto& fi : entries) {
        if (fi.isDir()) {
            if (fi.isHidden() || depth >= 2) continue;
            QString subCat = parentCategory;
            QString dirName = fi.fileName().toLower();
            if (dirName.contains("develop") || dirName.contains("visual studio")) subCat = "Development";
            else if (dirName.contains("game")) subCat = "Games";
            else if (dirName.contains("graphic") || dirName.contains("paint")) subCat = "Graphics";
            else if (dirName.contains("internet") || dirName.contains("browser") || dirName.contains("web")) subCat = "Internet";
            else if (dirName.contains("video") || dirName.contains("media") || dirName.contains("audio")) subCat = "Multimedia";
            else if (dirName.contains("office") || dirName.contains("document")) subCat = "Office";
            else if (dirName.contains("system") || dirName.contains("admin") || dirName.contains("accessories")) subCat = "System";
            else if (dirName.contains("util") || dirName.contains("tool")) subCat = "Utilities";

            crawlStartMenuDirectory(fi.absoluteFilePath(), subCat, depth + 1);
        } else if (fi.suffix().compare("lnk", Qt::CaseInsensitive) == 0) {
            QString baseName = fi.completeBaseName();
            // Fast duplicate check by name before doing expensive shell resolution
            bool alreadyExists = false;
            for (const auto& app : m_apps) {
                if (app.name.compare(baseName, Qt::CaseInsensitive) == 0) {
                    alreadyExists = true;
                    break;
                }
            }
            if (alreadyExists) continue;

            AppEntry entry;
            if (resolveShellLink(fi.absoluteFilePath(), entry)) {
                // Determine category
                if (!parentCategory.isEmpty() && m_categories.contains(parentCategory)) {
                    entry.category = parentCategory;
                } else {
                    entry.category = KWinWin::Uwp::UwpLauncher::categorizeApp(entry.name + " " + parentCategory, entry.execOrAumid);
                }

                if (!m_categories.contains(entry.category)) {
                    entry.category = "Applications";
                }

                QByteArray hash = QCryptographicHash::hash(entry.execOrAumid.toUtf8(), QCryptographicHash::Md5).toHex();
                entry.id = "win32_" + QString::fromLatin1(hash);

                // Deduplicate check against already indexed apps
                bool alreadyIndexed = false;
                for (const auto& existing : m_apps) {
                    if (existing.execOrAumid.compare(entry.execOrAumid, Qt::CaseInsensitive) == 0 ||
                        (existing.name.compare(entry.name, Qt::CaseInsensitive) == 0 && !entry.name.isEmpty())) {
                        alreadyIndexed = true;
                        break;
                    }
                }

                if (!alreadyIndexed) {
                    if (m_iconProvider && !entry.icon.isNull()) {
                        m_iconProvider->addIcon(entry.id, entry.icon);
                    }
                    m_apps.append(std::move(entry));
                }
            }
        }
    }
}

void AppModel::reloadApplications()
{
    m_apps.clear();
    if (m_iconProvider) {
        m_iconProvider->clear();
    }

    // 1. Crawl User Start Menu (depth 0, recurses into subfolders)
    PWSTR pUserPrograms = nullptr;
    if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_Programs, 0, nullptr, &pUserPrograms))) {
        QString userProgPath = QString::fromWCharArray(pUserPrograms);
        CoTaskMemFree(pUserPrograms);
        crawlStartMenuDirectory(userProgPath, "", 0);
    }

    // 2. Crawl Common Start Menu (depth 0, recurses into subfolders)
    PWSTR pCommonPrograms = nullptr;
    if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_CommonPrograms, 0, nullptr, &pCommonPrograms))) {
        QString commonProgPath = QString::fromWCharArray(pCommonPrograms);
        CoTaskMemFree(pCommonPrograms);
        crawlStartMenuDirectory(commonProgPath, "", 0);
    }

    // 3. Crawl Public Desktop (depth 2 means top-level only, no subfolder recursion)
    PWSTR pPublicDesktop = nullptr;
    if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_PublicDesktop, 0, nullptr, &pPublicDesktop))) {
        QString publicDesktopPath = QString::fromWCharArray(pPublicDesktop);
        CoTaskMemFree(pPublicDesktop);
        crawlStartMenuDirectory(publicDesktopPath, "", 2);
    }

    // 5. Enumerate UWP / MSIX Applications
    auto uwpApps = KWinWin::Uwp::UwpLauncher::enumerateInstalledApps();
    for (const auto& uwp : uwpApps) {
        AppEntry entry;
        entry.name = uwp.displayName;
        entry.execOrAumid = uwp.aumid;
        entry.category = uwp.category;
        entry.isUwp = true;

        if (!m_categories.contains(entry.category)) {
            entry.category = "Applications";
        }

        QByteArray hash = QCryptographicHash::hash(uwp.aumid.toUtf8(), QCryptographicHash::Md5).toHex();
        entry.id = "uwp_" + QString::fromLatin1(hash);

        // Deduplicate
        bool alreadyIndexed = false;
        for (const auto& existing : m_apps) {
            if (existing.execOrAumid.compare(entry.execOrAumid, Qt::CaseInsensitive) == 0 ||
                (existing.name.compare(entry.name, Qt::CaseInsensitive) == 0 && !entry.name.isEmpty())) {
                alreadyIndexed = true;
                break;
            }
        }
        if (alreadyIndexed) continue;

        // 1. Try extracting via IShellItemImageFactory from shell:AppsFolder
        std::wstring parsingName = L"shell:AppsFolder\\" + uwp.aumid.toStdWString();
        IShellItemImageFactory* pFactory = nullptr;
        if (SUCCEEDED(SHCreateItemFromParsingName(parsingName.c_str(), nullptr, IID_PPV_ARGS(&pFactory))) && pFactory) {
            HBITMAP hBitmap = nullptr;
            SIZE sz = { 48, 48 };
            if (SUCCEEDED(pFactory->GetImage(sz, SIIGBF_RESIZETOFIT | SIIGBF_ICONBACKGROUND, &hBitmap)) && hBitmap) {
                BITMAP bm{};
                GetObjectW(hBitmap, sizeof(bm), &bm);
                HDC hdcScreen = GetDC(nullptr);
                HDC hdcMem = CreateCompatibleDC(hdcScreen);

                BITMAPINFO bmi{};
                bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
                bmi.bmiHeader.biWidth = bm.bmWidth;
                bmi.bmiHeader.biHeight = -bm.bmHeight;
                bmi.bmiHeader.biPlanes = 1;
                bmi.bmiHeader.biBitCount = 32;
                bmi.bmiHeader.biCompression = BI_RGB;

                QImage image(bm.bmWidth, bm.bmHeight, QImage::Format_ARGB32_Premultiplied);
                GetDIBits(hdcMem, hBitmap, 0, bm.bmHeight, image.bits(), &bmi, DIB_RGB_COLORS);

                DeleteDC(hdcMem);
                ReleaseDC(nullptr, hdcScreen);
                DeleteObject(hBitmap);
                entry.icon = image;
            }
            pFactory->Release();
        }

        // 2. Fallback to resolveAppLogo
        if (entry.icon.isNull() && !uwp.logoPath.isEmpty()) {
            entry.icon = KWinWin::Uwp::UwpLauncher::resolveAppLogo(uwp.installPath, uwp.logoPath);
        }

        if (m_iconProvider && !entry.icon.isNull()) {
            m_iconProvider->addIcon(entry.id, entry.icon);
        }

        m_apps.append(std::move(entry));
    }

    // 6. Register Authentic KDE Plasma and WSLg Linux Applications (Zero TCP/IP)
    registerLinuxApps();

    // Sort apps alphabetically by name
    std::sort(m_apps.begin(), m_apps.end(), [](const AppEntry& a, const AppEntry& b) {
        return QString::compare(a.name, b.name, Qt::CaseInsensitive) < 0;
    });

    updateFilter();
    emit scanFinished();
    qInfo() << "[AppModel] Successfully indexed" << m_apps.size() << "applications (" << m_filteredIndices.size() << "matching filter).";
}

void AppModel::registerLinuxApp(const QString& id, const QString& name, const QString& exec, const QString& category, const QString& iconResource)
{
    AppEntry entry;
    entry.id = id;
    entry.name = name;
    entry.execOrAumid = exec;
    entry.category = category;
    entry.isLinux = true;
    entry.isUwp = false;

    if (!iconResource.isEmpty()) {
        entry.icon = QImage(iconResource);
        if (m_iconProvider && !entry.icon.isNull()) {
            m_iconProvider->addIcon(entry.id, entry.icon);
        }
    }

    m_apps.append(std::move(entry));
}

void AppModel::registerLinuxApps()
{
    // Authentic KDE Plasma 6 Breeze Desktop Applications
    registerLinuxApp("kde_dolphin", "Dolphin File Manager", "dolphin", "System", ":/icons/dolphin.png");
    registerLinuxApp("kde_konsole", "Konsole Terminal", "konsole", "System", ":/icons/konsole.png");
    registerLinuxApp("kde_systemsettings", "KDE System Settings", "systemsettings", "System", ":/icons/systemsettings.png");
    registerLinuxApp("kde_kate", "Kate Text Editor", "kate", "Development", ":/icons/kate.png");
    registerLinuxApp("kde_krunner", "KRunner Search Overlay", "krunner", "Utilities", ":/icons/krunner.png");
    registerLinuxApp("kde_sysmon", "KDE System Monitor", "plasma-systemmonitor", "System", ":/icons/sysmon.png");
    registerLinuxApp("kde_discover", "Discover Software Center", "plasma-discover", "System", ":/icons/discover.png");

    // Additional Linux Productivity & Internet Applications
    registerLinuxApp("linux_lowriter", "LibreOffice Writer", "libreoffice --writer", "Office", ":/icons/libreoffice-writer.png");
    registerLinuxApp("linux_localc", "LibreOffice Calc", "libreoffice --calc", "Office", ":/icons/libreoffice-calc.png");
    registerLinuxApp("linux_firefox", "Firefox Browser (Linux)", "firefox", "Internet", ":/icons/firefox.png");
    registerLinuxApp("linux_steam", "Steam (Linux)", "steam", "Games", ":/icons/steam.png");
}

void AppModel::launch(int index)
{
    if (index < 0 || index >= static_cast<int>(m_filteredIndices.size())) return;
    int actualIndex = m_filteredIndices[index];
    if (actualIndex < 0 || actualIndex >= m_apps.size()) return;
    const auto& app = m_apps.at(actualIndex);

    if (app.isLinux) {
        QString cmd = QString("export WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 QT_QPA_PLATFORM=wayland; nohup %1 %2 </dev/null >/dev/null 2>&1 &")
            .arg(app.execOrAumid, app.arguments);
        QProcess::startDetached("wsl.exe", QStringList() << "-d" << "Ubuntu" << "-u" << "jace479" << "-e" << "bash" << "-c" << cmd);
    } else if (app.isUwp) {
        KWinWin::Uwp::UwpLauncher::launchAumid(app.execOrAumid, app.arguments);
    } else {
        std::wstring wTarget = app.execOrAumid.toStdWString();
        std::wstring wArgs = app.arguments.toStdWString();
        std::wstring wDir = app.workingDir.toStdWString();

        ShellExecuteW(
            nullptr,
            L"open",
            wTarget.c_str(),
            app.arguments.isEmpty() ? nullptr : wArgs.c_str(),
            app.workingDir.isEmpty() ? nullptr : wDir.c_str(),
            SW_SHOWNORMAL
        );
    }
}

void AppModel::launchById(const QString& id)
{
    for (int i = 0; i < m_apps.size(); ++i) {
        if (m_apps[i].id == id) {
            const auto& app = m_apps.at(i);
            if (app.isLinux) {
                QString cmd = QString("export WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 QT_QPA_PLATFORM=wayland; nohup %1 %2 </dev/null >/dev/null 2>&1 &")
                    .arg(app.execOrAumid, app.arguments);
                QProcess::startDetached("wsl.exe", QStringList() << "-d" << "Ubuntu" << "-u" << "jace479" << "-e" << "bash" << "-c" << cmd);
            } else if (app.isUwp) {
                KWinWin::Uwp::UwpLauncher::launchAumid(app.execOrAumid, app.arguments);
            } else {
                std::wstring wTarget = app.execOrAumid.toStdWString();
                std::wstring wArgs = app.arguments.toStdWString();
                std::wstring wDir = app.workingDir.toStdWString();

                ShellExecuteW(
                    nullptr,
                    L"open",
                    wTarget.c_str(),
                    app.arguments.isEmpty() ? nullptr : wArgs.c_str(),
                    app.workingDir.isEmpty() ? nullptr : wDir.c_str(),
                    SW_SHOWNORMAL
                );
            }
            return;
        }
    }
}

} // namespace KWinWin::UI
