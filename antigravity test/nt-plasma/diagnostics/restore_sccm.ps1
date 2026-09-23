Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;

public class SccmFixer {
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
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    public const int GWL_STYLE = -16;
    public const int GWL_EXSTYLE = -20;
    public const long WS_CAPTION = 0x00C00000L;
    public const long WS_THICKFRAME = 0x00040000L;
    public const long WS_MINIMIZEBOX = 0x00020000L;
    public const long WS_MAXIMIZEBOX = 0x00010000L;
    public const long WS_SYSMENU = 0x00080000L;
    public const long WS_CHILD = 0x40000000L;
    public const long WS_POPUP = 0x80000000L;
    public const uint SWP_FRAMECHANGED = 0x0020;
    public const uint SWP_NOMOVE = 0x0002;
    public const uint SWP_NOSIZE = 0x0001;
    public const uint SWP_NOZORDER = 0x0004;
    public const uint SWP_NOACTIVATE = 0x0010;
    public const uint SWP_DRAWFRAME = 0x0020;

    public static void FindAndFixAll() {
        EnumWindows((hWnd, lParam) => {
            if (!IsWindowVisible(hWnd)) return true;

            var title = new StringBuilder(512);
            GetWindowText(hWnd, title, 512);
            var cls = new StringBuilder(512);
            GetClassName(hWnd, cls, 512);

            string sTitle = title.ToString();
            string sCls = cls.ToString();

            uint pid = 0;
            GetWindowThreadProcessId(hWnd, out pid);

            long style = GetWindowLongPtr(hWnd, GWL_STYLE).ToInt64();
            long exStyle = GetWindowLongPtr(hWnd, GWL_EXSTYLE).ToInt64();

            if ((style & WS_CHILD) != 0) return true;

            // Check if title or class relates to SCCM, ConfigMgr, MMC, or any window missing caption
            bool isTarget = sTitle.IndexOf("Configuration Manager", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            sTitle.IndexOf("ConfigMgr", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            sTitle.IndexOf("SCCM", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            sTitle.IndexOf("Microsoft Endpoint", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            sCls.IndexOf("MMC", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            sCls.IndexOf("Console", StringComparison.OrdinalIgnoreCase) >= 0;

            if (isTarget || (!string.IsNullOrEmpty(sTitle) && ((style & WS_CAPTION) == 0 || (style & WS_THICKFRAME) == 0))) {
                if (sCls != "Progman" && sCls != "WorkerW" && sCls != "Shell_TrayWnd" && sCls != "Shell_SecondaryTrayWnd") {
                    Console.WriteLine(string.Format("[Found] HWND=0x{0:X}, PID={1}, Title='{2}', Class='{3}', Style=0x{4:X}", hWnd.ToInt64(), pid, sTitle, sCls, style));
                    
                    // Force standard overlapped window style with caption, resizable frame, minimize, maximize, sysmenu
                    long newStyle = (style & ~WS_POPUP) | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU;
                    SetWindowLongPtr(hWnd, GWL_STYLE, new IntPtr(newStyle));

                    SetWindowPos(hWnd, IntPtr.Zero, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_DRAWFRAME);
                    
                    Console.WriteLine(string.Format(" -> Restored Style to 0x{0:X}", newStyle));
                }
            }

            return true;
        }, IntPtr.Zero);
    }
}
'@

Write-Host "Scanning for SCCM Console and restoring frames..." -ForegroundColor Cyan
[SccmFixer]::FindAndFixAll()
Write-Host "Scan and repair complete." -ForegroundColor Green
