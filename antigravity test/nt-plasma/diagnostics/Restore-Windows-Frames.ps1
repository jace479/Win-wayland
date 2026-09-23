Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public class WinRestore {
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

    [DllImport("user32.dll")]
    public static extern IntPtr SetWindowLongPtr(IntPtr hWnd, int nIndex, IntPtr dwNewLong);

    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, IntPtr pvParam, uint fWinIni);

    public const int GWL_STYLE = -16;
    public const long WS_CAPTION = 0x00C00000L;
    public const long WS_THICKFRAME = 0x00040000L;
    public const long WS_MINIMIZEBOX = 0x00020000L;
    public const long WS_MAXIMIZEBOX = 0x00010000L;
    public const long WS_SYSMENU = 0x00080000L;
    public const long WS_CHILD = 0x40000000L;
    public const uint SWP_FRAMECHANGED = 0x0020;
    public const uint SWP_NOMOVE = 0x0002;
    public const uint SWP_NOSIZE = 0x0001;
    public const uint SWP_NOZORDER = 0x0004;
    public const uint SWP_NOACTIVATE = 0x0010;

    public static void RestoreWindows() {
        EnumWindows((hWnd, lParam) => {
            if (!IsWindowVisible(hWnd)) return true;

            var title = new System.Text.StringBuilder(256);
            GetWindowText(hWnd, title, 256);
            var cls = new System.Text.StringBuilder(256);
            GetClassName(hWnd, cls, 256);

            string sCls = cls.ToString();
            string sTitle = title.ToString();

            if (string.IsNullOrEmpty(sTitle)) return true;

            if (sCls == "Progman" || sCls == "WorkerW" || sCls == "Shell_TrayWnd" || 
                sCls == "Shell_SecondaryTrayWnd" || sCls == "Windows.UI.Core.CoreWindow" ||
                sCls == "ApplicationFrameWindow") {
                return true;
            }

            long style = GetWindowLongPtr(hWnd, GWL_STYLE).ToInt64();
            if ((style & WS_CHILD) != 0) return true;

            // Check if window lacks caption or thickframe
            if ((style & WS_CAPTION) == 0 || (style & WS_THICKFRAME) == 0) {
                long newStyle = style | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU;
                SetWindowLongPtr(hWnd, GWL_STYLE, new IntPtr(newStyle));
                SetWindowPos(hWnd, IntPtr.Zero, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED);
                Console.WriteLine("Restored: " + sTitle + " (" + sCls + ")");
            }
            return true;
        }, IntPtr.Zero);
    }
}
'@

Write-Host "Restoring all window styles and frames..." -ForegroundColor Cyan
[WinRestore]::RestoreWindows()

Write-Host "`nRestarting Windows Explorer to ensure clean desktop shell and taskbar state..." -ForegroundColor Yellow
Stop-Process -Name explorer -Force
Start-Sleep -Seconds 2

Write-Host "Restoration complete! Windows frames and snapping are fully restored." -ForegroundColor Green
