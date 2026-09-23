<#
.SYNOPSIS
    Hides or reveals Windows Explorer taskbar and desktop surfaces for hybrid preview.

.DESCRIPTION
    Uses Win32 ShowWindow to toggle visibility of:
    - Primary Taskbar (Shell_TrayWnd)
    - Secondary Taskbars (Shell_SecondaryTrayWnd)
    - Desktop surface icons (Progman / WorkerW)
    Useful during testing and shell-preview mode when Explorer is kept alive in background.

.PARAMETER Action
    'Hide' to conceal Explorer shell components; 'Show' to restore them.
#>
[CmdletBinding()]
param(
    [ValidateSet('Hide', 'Show')]
    [string]$Action = 'Hide'
)

$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class ShellHider
{
    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr FindWindowEx(IntPtr parentHandle, IntPtr childAfter, string className, string windowTitle);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    public const int SW_HIDE = 0;
    public const int SW_SHOW = 5;

    public static void SetVisibility(bool show)
    {
        int cmd = show ? SW_SHOW : SW_HIDE;

        // Primary Taskbar
        IntPtr primaryTray = FindWindow("Shell_TrayWnd", null);
        if (primaryTray != IntPtr.Zero)
        {
            ShowWindow(primaryTray, cmd);
        }

        // Secondary Taskbars (multi-monitor)
        IntPtr secondaryTray = IntPtr.Zero;
        while ((secondaryTray = FindWindowEx(IntPtr.Zero, secondaryTray, "Shell_SecondaryTrayWnd", null)) != IntPtr.Zero)
        {
            ShowWindow(secondaryTray, cmd);
        }

        // Desktop Surface
        IntPtr progman = FindWindow("Progman", null);
        if (progman != IntPtr.Zero)
        {
            ShowWindow(progman, cmd);
        }
    }
}
"@ -ErrorAction SilentlyContinue

$show = ($Action -eq 'Show')
[ShellHider]::SetVisibility($show)
Write-Output "Explorer shell components set to: $Action"
