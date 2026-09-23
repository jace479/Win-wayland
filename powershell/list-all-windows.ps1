Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Collections.Generic;

public class AllWinInspector {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);
    [DllImport("user32.dll")]
    public static extern bool SetThreadDesktop(IntPtr hDesktop);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public static void ListAll() {
        IntPtr hDesk = OpenDesktop("Default", 0, false, 0x01FF);
        if (hDesk != IntPtr.Zero) {
            SetThreadDesktop(hDesk);
        }

        int count = 0;
        EnumWindows((hWnd, lParam) => {
            count++;
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            bool vis = IsWindowVisible(hWnd);

            RECT r;
            GetWindowRect(hWnd, out r);
            int w = r.Right - r.Left;
            int h = r.Bottom - r.Top;

            StringBuilder title = new StringBuilder(512);
            GetWindowText(hWnd, title, 512);
            StringBuilder cls = new StringBuilder(512);
            GetClassName(hWnd, cls, 512);

            string procName = "unknown";
            try { procName = Process.GetProcessById((int)pid).ProcessName; } catch {}

            if (procName.ToLower().Contains("msrdc") || procName.ToLower().Contains("wsl") || vis) {
                if (w > 0 && h > 0) {
                    Console.WriteLine(string.Format("PID {0} ({1}) | HWND: 0x{2:X} | Vis: {3} | Rect: ({4},{5})-({6},{7}) [{8}x{9}] | Class: '{10}' | Title: '{11}'",
                        pid, procName, hWnd.ToInt64(), vis, r.Left, r.Top, r.Right, r.Bottom, w, h, cls.ToString(), title.ToString()));
                }
            }
            return true;
        }, IntPtr.Zero);
        Console.WriteLine("Total windows evaluated: " + count);
    }
}
"@

[AllWinInspector]::ListAll()
