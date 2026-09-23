Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Diagnostics;

public class WinEnum {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public static void ListMsrdcWindows() {
        EnumWindows((hWnd, lParam) => {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            StringBuilder title = new StringBuilder(256);
            GetWindowText(hWnd, title, 256);
            StringBuilder cls = new StringBuilder(256);
            GetClassName(hWnd, cls, 256);
            bool vis = IsWindowVisible(hWnd);
            try {
                var proc = Process.GetProcessById((int)pid);
                if (proc.ProcessName.ToLower().Contains("msrdc")) {
                    RECT r;
                    GetWindowRect(hWnd, out r);
                    Console.WriteLine(string.Format("PID: {0} | HWND: 0x{1:X} | Vis: {2} | Size: {3}x{4} at ({5},{6}) | Class: '{7}' | Title: '{8}'",
                        pid, hWnd.ToInt64(), vis, r.Right - r.Left, r.Bottom - r.Top, r.Left, r.Top, cls.ToString(), title.ToString()));
                }
            } catch {}
            return true;
        }, IntPtr.Zero);
    }
}
"@

[WinEnum]::ListMsrdcWindows()
