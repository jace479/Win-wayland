#include "UwpLauncher.hpp"
#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <tlhelp32.h>

// C++/WinRT headers
#include <winrt/base.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Management.Deployment.h>
#include <winrt/Windows.ApplicationModel.h>
#include <winrt/Windows.ApplicationModel.Core.h>
#include <winrt/Windows.Storage.h>

namespace KWinWin::Uwp {

UwpLauncher::UwpLauncher() = default;
UwpLauncher::~UwpLauncher() = default;

bool UwpLauncher::isProcessRunning(const wchar_t* processName)
{
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) {
        return false;
    }

    PROCESSENTRY32W entry{};
    entry.dwSize = sizeof(entry);

    bool found = false;
    if (Process32FirstW(snapshot, &entry)) {
        do {
            if (_wcsicmp(entry.szExeFile, processName) == 0) {
                found = true;
                break;
            }
        } while (Process32NextW(snapshot, &entry));
    }

    CloseHandle(snapshot);
    return found;
}

bool UwpLauncher::ensureShellInfrastructureHost()
{
    if (isProcessRunning(L"sihost.exe")) {
        qInfo() << "[UwpLauncher] Shell Infrastructure Host (sihost.exe) is already active.";
        return true;
    }

    qInfo() << "[UwpLauncher] Spawning C:\\Windows\\System32\\sihost.exe...";

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};

    wchar_t cmd[] = L"C:\\Windows\\System32\\sihost.exe";
    BOOL success = CreateProcessW(
        nullptr, cmd, nullptr, nullptr, FALSE,
        CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
        nullptr, nullptr, &si, &pi
    );

    if (success) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        qInfo() << "[UwpLauncher] sihost.exe successfully spawned.";
        return true;
    } else {
        qWarning() << "[UwpLauncher] Failed to launch sihost.exe. Error code:" << GetLastError();
        return false;
    }
}

bool UwpLauncher::launchAumid(const QString& aumid, const QString& arguments)
{
    IApplicationActivationManager* pActMgr = nullptr;
    HRESULT hr = CoCreateInstance(
        CLSID_ApplicationActivationManager,
        nullptr,
        CLSCTX_LOCAL_SERVER,
        IID_PPV_ARGS(&pActMgr)
    );

    if (FAILED(hr) || !pActMgr) {
        qWarning() << "[UwpLauncher] Failed to create IApplicationActivationManager instance. HR:" << Qt::hex << hr;
        return false;
    }

    DWORD processId = 0;
    std::wstring wAumid = aumid.toStdWString();
    std::wstring wArgs = arguments.toStdWString();

    hr = pActMgr->ActivateApplication(
        wAumid.c_str(),
        arguments.isEmpty() ? nullptr : wArgs.c_str(),
        AO_NONE,
        &processId
    );

    pActMgr->Release();

    if (SUCCEEDED(hr)) {
        qInfo() << "[UwpLauncher] Activated AUMID:" << aumid << "Process ID:" << processId;
        return true;
    } else {
        qWarning() << "[UwpLauncher] Activation failed for AUMID:" << aumid << "HR:" << Qt::hex << hr;
        return false;
    }
}

bool UwpLauncher::launchProtocol(const QString& uri)
{
    std::wstring wUri = uri.toStdWString();
    HINSTANCE hInst = ShellExecuteW(nullptr, L"open", wUri.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
    auto result = reinterpret_cast<INT_PTR>(hInst);
    if (result > 32) {
        qInfo() << "[UwpLauncher] Successfully launched protocol URI:" << uri;
        return true;
    }
    qWarning() << "[UwpLauncher] Failed to launch protocol URI:" << uri << "Code:" << result;
    return false;
}

QString UwpLauncher::categorizeApp(const QString& appName, const QString& aumid)
{
    QString combined = (appName + " " + aumid).toLower();

    if (combined.contains("code") || combined.contains("develop") || combined.contains("git") ||
        combined.contains("visual studio") || combined.contains("terminal") || combined.contains("powershell") ||
        combined.contains("cmd") || combined.contains("python") || combined.contains("clion") ||
        combined.contains("rust") || combined.contains("node") || combined.contains("npm") ||
        combined.contains("compiler") || combined.contains("devenv")) {
        return "Development";
    }
    if (combined.contains("game") || combined.contains("play") || combined.contains("steam") ||
        combined.contains("xbox") || combined.contains("minecraft") || combined.contains("riot") ||
        combined.contains("epic") || combined.contains("gog") || combined.contains("battle.net") ||
        combined.contains("origin") || combined.contains("ea app")) {
        return "Games";
    }
    if (combined.contains("paint") || combined.contains("draw") || combined.contains("photo") ||
        combined.contains("image") || combined.contains("snip") || combined.contains("gimp") ||
        combined.contains("blender") || combined.contains("photoshop") || combined.contains("illustrator") ||
        combined.contains("canva") || combined.contains("inkscape") || combined.contains("canvas")) {
        return "Graphics";
    }
    if (combined.contains("chrome") || combined.contains("edge") || combined.contains("firefox") ||
        combined.contains("browser") || combined.contains("internet") || combined.contains("web") ||
        combined.contains("discord") || combined.contains("telegram") || combined.contains("slack") ||
        combined.contains("zoom") || combined.contains("teams") || combined.contains("skype") ||
        combined.contains("thunderbird") || combined.contains("brave") || combined.contains("opera") ||
        combined.contains("vivaldi") || combined.contains("torrent")) {
        return "Internet";
    }
    if (combined.contains("media") || combined.contains("music") || combined.contains("video") ||
        combined.contains("sound") || combined.contains("audio") || combined.contains("spotify") ||
        combined.contains("player") || combined.contains("vlc") || combined.contains("itunes") ||
        combined.contains("foobar") || combined.contains("obs") || combined.contains("film")) {
        return "Multimedia";
    }
    if (combined.contains("word") || combined.contains("excel") || combined.contains("powerpoint") ||
        combined.contains("office") || combined.contains("onenote") || combined.contains("mail") ||
        combined.contains("outlook") || combined.contains("calendar") || combined.contains("pdf") ||
        combined.contains("acrobat") || combined.contains("reader") || combined.contains("access")) {
        return "Office";
    }
    if (combined.contains("setting") || combined.contains("control") || combined.contains("task") ||
        combined.contains("system") || combined.contains("security") || combined.contains("defender") ||
        combined.contains("registry") || combined.contains("device") || combined.contains("disk") ||
        combined.contains("cleanup") || combined.contains("defrag") || combined.contains("eventvwr") ||
        combined.contains("services") || combined.contains("msconfig") || combined.contains("admin")) {
        return "System";
    }
    if (combined.contains("calc") || combined.contains("clock") || combined.contains("map") ||
        combined.contains("weather") || combined.contains("tool") || combined.contains("utility") ||
        combined.contains("notepad") || combined.contains("7-zip") || combined.contains("winrar") ||
        combined.contains("archive") || combined.contains("camera") || combined.contains("recorder")) {
        return "Utilities";
    }

    return "Applications";
}

QImage UwpLauncher::resolveAppLogo(const QString& packageInstallPath, const QString& relativeLogo)
{
    if (relativeLogo.isEmpty()) {
        return {};
    }

    QDir dir(packageInstallPath);
    QString cleanRel = relativeLogo;
    cleanRel.replace('\\', '/');

    // Check direct path first
    QString directPath = dir.filePath(cleanRel);
    if (QFile::exists(directPath)) {
        return QImage(directPath);
    }

    // Attempt resolving targetsize and scale suffixes
    QFileInfo fi(directPath);
    QString baseName = fi.completeBaseName();
    QString suffix = fi.suffix();
    QDir assetDir = fi.dir();

    QStringList candidates = {
        baseName + ".targetsize-48." + suffix,
        baseName + ".targetsize-32." + suffix,
        baseName + ".targetsize-24." + suffix,
        baseName + ".scale-100." + suffix,
        baseName + ".scale-125." + suffix,
        baseName + ".scale-150." + suffix,
        baseName + ".scale-200." + suffix
    };

    for (const QString& cand : candidates) {
        QString fullCand = assetDir.filePath(cand);
        if (QFile::exists(fullCand)) {
            return QImage(fullCand);
        }
    }

    return {};
}

std::vector<UwpAppInfo> UwpLauncher::enumerateInstalledApps()
{
    std::vector<UwpAppInfo> results;

    try {
        winrt::Windows::Management::Deployment::PackageManager packageManager;
        auto packages = packageManager.FindPackagesForUser(L"");

        for (const auto& package : packages) {
            try {
                if (package.IsFramework() || package.IsResourcePackage() || package.IsOptional()) {
                    continue;
                }

                auto entries = package.GetAppListEntriesAsync().get();
                for (const auto& entry : entries) {
                    UwpAppInfo info;
                    info.displayName = QString::fromWCharArray(entry.DisplayInfo().DisplayName().c_str());
                    info.aumid = QString::fromWCharArray(entry.AppUserModelId().c_str());
                    info.packageFamilyName = QString::fromWCharArray(package.Id().FamilyName().c_str());

                    std::wstring installPath = package.InstalledLocation() ? package.InstalledLocation().Path().c_str() : L"";
                    info.installPath = QString::fromWCharArray(installPath.c_str());

                    info.category = categorizeApp(info.displayName, info.aumid);

                    if (!info.displayName.isEmpty() && !info.aumid.isEmpty()) {
                        results.push_back(std::move(info));
                    }
                }
            } catch (...) {
                // Ignore individual package retrieval errors
            }
        }
    } catch (const winrt::hresult_error& ex) {
        qWarning() << "[UwpLauncher] WinRT PackageManager error:" << QString::fromWCharArray(ex.message().c_str());
    } catch (...) {
        qWarning() << "[UwpLauncher] Unknown error during UWP app enumeration.";
    }

    return results;
}

} // namespace KWinWin::Uwp
