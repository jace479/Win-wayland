using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

namespace NtPlasma.DesktopSurfaceHost;

internal static class ExplorerHider
{
    private const int SwHide = 0;
    private const int SwShow = 5;

    [DllImport("user32.dll")]
    private static extern nint OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll")]
    private static extern bool CloseDesktop(nint hDesktop);

    private delegate bool EnumDesktopWindowsProc(nint hWnd, nint lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumDesktopWindows(nint hDesktop, EnumDesktopWindowsProc lpfn, nint lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumDesktopWindowsProc lpEnumFunc, nint lParam);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern int GetClassName(nint hWnd, StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern nint FindWindowEx(nint parent, nint childAfter, string className, string? title);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(nint hWnd, int nCmdShow);

    private static bool? _currentVisibility = null;

    public static void SetVisibility(bool show)
    {
        if (_currentVisibility == show) return;
        _currentVisibility = show;

        var cmd = show ? SwShow : SwHide;
        var targets = new List<nint>();
        nint progmanHwnd = nint.Zero;

        bool EnumCallback(nint hWnd, nint lParam)
        {
            var sb = new StringBuilder(256);
            GetClassName(hWnd, sb, sb.Capacity);
            var cls = sb.ToString();

            if (cls is "Shell_TrayWnd" or "Shell_SecondaryTrayWnd")
            {
                targets.Add(hWnd);
            }
            return true;
        }

        nint hDesk = OpenDesktop("default", 0, false, 0x01FF);
        if (hDesk != nint.Zero)
        {
            try
            {
                EnumDesktopWindows(hDesk, EnumCallback, nint.Zero);
            }
            finally
            {
                CloseDesktop(hDesk);
            }
        }

        if (targets.Count == 0)
        {
            EnumWindows(EnumCallback, nint.Zero);
        }

        foreach (var hWnd in targets)
        {
            ShowWindow(hWnd, cmd);
        }
    }
}

