Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public class WindowInspector
{
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")]
    public static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public static void InspectAndBringToFront(IntPtr hWnd)
    {
        RECT r;
        GetWindowRect(hWnd, out r);
        IntPtr style = GetWindowLongPtr(hWnd, -16);
        IntPtr exStyle = GetWindowLongPtr(hWnd, -20);
        bool vis = IsWindowVisible(hWnd);
        Console.WriteLine(string.Format("HWND: 0x{0:X} | Rect: ({1},{2})-({3},{4}) [Size: {5}x{6}] | Vis: {7} | Style: 0x{8:X} | ExStyle: 0x{9:X}",
            hWnd.ToInt64(), r.Left, r.Top, r.Right, r.Bottom, r.Right - r.Left, r.Bottom - r.Top, vis, style.ToInt64(), exStyle.ToInt64()));

        // Bring to front, ensure restored and visible
        ShowWindow(hWnd, 9); // SW_RESTORE
        ShowWindow(hWnd, 5); // SW_SHOW
        BringWindowToTop(hWnd);
        SetForegroundWindow(hWnd);
        SetWindowPos(hWnd, new IntPtr(-1), 100, 100, 1024, 768, 0x0040); // HWND_TOPMOST, SWP_SHOWWINDOW
        Console.WriteLine("Sent SW_RESTORE, SW_SHOW, SetForegroundWindow, and positioned at (100,100,1024,768)");
    }
}
"@

$msrdcProc = Get-Process msrdc -ErrorAction SilentlyContinue
if ($msrdcProc) {
    Write-Host "Found MSRDC processes:"
    $msrdcProc | Format-Table Id, ProcessName, MainWindowHandle
}

# Use the discovered HWND
[WindowInspector]::InspectAndBringToFront([IntPtr]0x4B06DE)
