using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;

namespace NtPlasma.DesktopSurfaceHost;

/// <summary>
/// Pre-flight health checks for WSL before launching any WSL-dependent subsystem.
/// Prevents hangs when WSL is unavailable, the distro is missing, or KDE is not installed.
/// </summary>
internal sealed class WslHealthGate
{
    private const string DistroName = "Ubuntu";
    private const int TimeoutMs = 10_000;

    public sealed record HealthReport(
        bool IsReady,
        bool WslAvailable,
        bool DistroRegistered,
        bool DistroBoots,
        bool PlasmaInstalled,
        bool X11Available,
        string FailureReason,
        string DesktopFlavor = "None",
        bool CoreAppsInstalled = false,
        bool ThemesInstalled = false);

    /// <summary>
    /// Runs all health checks and returns a report. Safe to call from any thread.
    /// </summary>
    public static HealthReport Check()
    {
        var checks = new List<string>();

        // 1. Is wsl.exe available?
        if (!File.Exists(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "wsl.exe")))
        {
            return Fail(wslAvailable: false, reason: "wsl.exe not found in System32");
        }

        // 2. Is the distro registered?
        var listResult = RunWsl("--list --quiet", 5_000);
        if (!listResult.Success)
        {
            return Fail(wslAvailable: false, reason: $"wsl --list failed: {listResult.Error}");
        }
        if (!listResult.Output.Contains(DistroName, StringComparison.OrdinalIgnoreCase))
        {
            return Fail(wslAvailable: true, distroRegistered: false,
                reason: $"WSL distro '{DistroName}' is not registered. Registered: {listResult.Output.Trim()}");
        }

        // 3. Can the distro boot and execute?
        var bootResult = RunWsl($"-d {DistroName} -- echo NTKDE_READY", TimeoutMs);
        if (!bootResult.Success || !bootResult.Output.Contains("NTKDE_READY"))
        {
            return Fail(wslAvailable: true, distroRegistered: true, distroBoots: false,
                reason: $"WSL distro '{DistroName}' failed to boot: {bootResult.Error}");
        }

        // 4. Is plasmashell installed?
        var plasmaResult = RunWsl($"-d {DistroName} -- test -x /usr/bin/plasmashell && echo PLASMA_OK", TimeoutMs);
        bool plasmaInstalled = plasmaResult.Success && plasmaResult.Output.Contains("PLASMA_OK");
        if (!plasmaInstalled)
        {
            checks.Add("plasmashell not installed (run provision/install-desktop.sh kubuntu)");
        }

        // 5. Is X11 (libX11) available? (Required by kde-task-bridge.py)
        var x11Result = RunWsl(
            $"-d {DistroName} -- python3 -c \"import ctypes; ctypes.cdll.LoadLibrary('libX11.so.6'); print('X11_OK')\"",
            TimeoutMs);
        bool x11Available = x11Result.Success && x11Result.Output.Contains("X11_OK");
        if (!x11Available)
        {
            checks.Add("libX11.so.6 not available (install libx11-6)");
        }

        // 6. Check for core desktop apps (dolphin, konsole)
        var appsResult = RunWsl(
            $"-d {DistroName} -- bash -c \"(which dolphin && which konsole) >/dev/null 2>&1 && echo APPS_OK\"",
            TimeoutMs);
        bool coreAppsInstalled = appsResult.Success && appsResult.Output.Contains("APPS_OK");

        // 7. Check for Breeze icons / themes
        var themeResult = RunWsl(
            $"-d {DistroName} -- test -d /usr/share/icons/breeze && echo THEME_OK",
            TimeoutMs);
        bool themesInstalled = themeResult.Success && themeResult.Output.Contains("THEME_OK");

        // Determine desktop flavor
        string desktopFlavor = "None";
        if (plasmaInstalled)
        {
            if (coreAppsInstalled && themesInstalled)
            {
                desktopFlavor = "Kubuntu Full";
            }
            else
            {
                desktopFlavor = "KDE Plasma Minimal";
                checks.Add("Full desktop recommended (run provision/install-desktop.sh kubuntu)");
            }
        }

        // If critical checks pass, we're ready (plasma/x11 are warnings not blockers for tray mode)
        bool isReady = true;
        string failureReason = "";
        if (!plasmaInstalled && !x11Available)
        {
            isReady = false;
            failureReason = string.Join("; ", checks);
        }

        return new HealthReport(
            IsReady: isReady,
            WslAvailable: true,
            DistroRegistered: true,
            DistroBoots: true,
            PlasmaInstalled: plasmaInstalled,
            X11Available: x11Available,
            FailureReason: failureReason,
            DesktopFlavor: desktopFlavor,
            CoreAppsInstalled: coreAppsInstalled,
            ThemesInstalled: themesInstalled);
    }

    /// <summary>
    /// Quick check: can we reach WSL at all? Faster than full Check().
    /// </summary>
    public static bool QuickPing()
    {
        var result = RunWsl($"-d {DistroName} -- echo PING", 5_000);
        return result.Success && result.Output.Contains("PING");
    }

    private static HealthReport Fail(
        bool wslAvailable = false,
        bool distroRegistered = false,
        bool distroBoots = false,
        bool plasmaInstalled = false,
        bool x11Available = false,
        string reason = "",
        string desktopFlavor = "None",
        bool coreAppsInstalled = false,
        bool themesInstalled = false)
    {
        return new HealthReport(
            IsReady: false,
            WslAvailable: wslAvailable,
            DistroRegistered: distroRegistered,
            DistroBoots: distroBoots,
            PlasmaInstalled: plasmaInstalled,
            X11Available: x11Available,
            FailureReason: reason,
            DesktopFlavor: desktopFlavor,
            CoreAppsInstalled: coreAppsInstalled,
            ThemesInstalled: themesInstalled);
    }

    private sealed record WslResult(bool Success, string Output, string Error);

    private static WslResult RunWsl(string arguments, int timeoutMs)
    {
        try
        {
            var psi = new ProcessStartInfo("wsl.exe", arguments)
            {
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            };

            using var process = Process.Start(psi);
            if (process == null)
            {
                return new WslResult(false, "", "Failed to start wsl.exe");
            }

            var output = process.StandardOutput.ReadToEnd().Replace("\0", "");
            var error = process.StandardError.ReadToEnd().Replace("\0", "");

            if (!process.WaitForExit(timeoutMs))
            {
                try { process.Kill(); } catch { }
                return new WslResult(false, output, $"Timed out after {timeoutMs}ms");
            }

            return new WslResult(process.ExitCode == 0, output, error);
        }
        catch (Exception ex)
        {
            return new WslResult(false, "", ex.Message);
        }
    }
}
