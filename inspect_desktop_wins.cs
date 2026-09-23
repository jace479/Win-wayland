using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Diagnostics;

public class InspectDesktopWins {
    [DllImport("user32.dll")] public static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpfn, IntPtr lParam);
    [DllImport("user32.dll")] public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);
    [DllImport("user32.dll")] public static extern bool CloseDesktop(IntPtr hDesktop);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] public static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }

    public static void Main(string[] args) {
        IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
        EnumDesktopWindows(hDesk, (hWnd, lParam) => {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            try {
                var proc = Process.GetProcessById((int)pid);
                if (proc.ProcessName.ToLower().Contains("msrdc")) {
                    StringBuilder title = new StringBuilder(256);
                    GetWindowText(hWnd, title, 256);
                    if (title.ToString().Contains("Desktop @")) {
                        RECT r;
                        GetWindowRect(hWnd, out r);
                        Console.WriteLine(string.Format("FOUND: 0x{0:X} | Vis: {1} | Rect: [{2},{3}->{4},{5}] | Title: '{6}'",
                            hWnd.ToInt64(), IsWindowVisible(hWnd), r.Left, r.Top, r.Right, r.Bottom, title.ToString()));
                        if (args.Length > 0 && args[0] == "show") {
                            ShowWindow(hWnd, 8 /* SW_SHOWNA */);
                            Console.WriteLine("Shown window 0x" + hWnd.ToString("X"));
                        }
                    }
                }
            } catch {}
            return true;
        }, IntPtr.Zero);
        CloseDesktop(hDesk);
    }
}
