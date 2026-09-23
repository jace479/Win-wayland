#pragma once

#include <string>
#include <vector>
#include <windows.h>
#include <shobjidl.h>
#include <QString>
#include <QIcon>
#include <QImage>

namespace KWinWin::Uwp {

struct UwpAppInfo {
    QString displayName;
    QString aumid;               // AppUserModelId
    QString packageFamilyName;
    QString installPath;
    QString logoPath;
    QString category;            // FreeDesktop / KDE category
};

class UwpLauncher {
public:
    UwpLauncher();
    ~UwpLauncher();

    // Spawns C:\Windows\System32\sihost.exe if not already active
    static bool ensureShellInfrastructureHost();

    // Launches modern UWP / MSIX application via IApplicationActivationManager
    static bool launchAumid(const QString& aumid, const QString& arguments = QString());

    // Launches standard Windows URI protocols (e.g. "ms-settings:", "calc:")
    static bool launchProtocol(const QString& uri);

    // Enumerates installed UWP/MSIX applications using C++/WinRT PackageManager
    static std::vector<UwpAppInfo> enumerateInstalledApps();

    // Categorization helper mapping WinRT manifest capabilities / names to KDE categories
    static QString categorizeApp(const QString& appName, const QString& aumid);

    // Resolves UWP app logo to QImage
    static QImage resolveAppLogo(const QString& packageInstallPath, const QString& relativeLogo);

private:
    static bool isProcessRunning(const wchar_t* processName);
};

} // namespace KWinWin::Uwp
