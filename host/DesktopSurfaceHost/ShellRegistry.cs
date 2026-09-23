using System.Diagnostics;
using Microsoft.Win32;

namespace NtPlasma.DesktopSurfaceHost;

internal static class ShellRegistry
{
    private const string WinlogonKeyPath = @"Software\Microsoft\Windows NT\CurrentVersion\Winlogon";

    public static bool SetShell(string? shellExecutablePath = null)
    {
        shellExecutablePath ??= Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName;
        if (string.IsNullOrWhiteSpace(shellExecutablePath))
        {
            return false;
        }

        using var key = Registry.CurrentUser.CreateSubKey(WinlogonKeyPath);
        var existing = key.GetValue("Shell") as string;
        if (!string.IsNullOrEmpty(existing) && key.GetValue("ntKDE_OriginalShell") is null)
        {
            key.SetValue("ntKDE_OriginalShell", existing);
        }

        key.SetValue("Shell", shellExecutablePath);
        return true;
    }

    public static bool RestoreShell()
    {
        using var key = Registry.CurrentUser.OpenSubKey(WinlogonKeyPath, writable: true);
        if (key != null)
        {
            key.DeleteValue("Shell", throwOnMissingValue: false);
            key.DeleteValue("ntKDE_OriginalShell", throwOnMissingValue: false);
        }

        if (Process.GetProcessesByName("explorer").Length == 0)
        {
            try
            {
                Process.Start(new ProcessStartInfo("explorer.exe") { UseShellExecute = true });
            }
            catch
            {
            }
        }

        return true;
    }

    public static string GetCurrentShell()
    {
        using var key = Registry.CurrentUser.OpenSubKey(WinlogonKeyPath);
        var shell = key?.GetValue("Shell") as string;
        return string.IsNullOrWhiteSpace(shell) ? "explorer.exe (system default)" : shell;
    }
}
