Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Collections.Generic;

public class MsrdcDeepInspector {
    public delegate bool EnumThreadDelegate(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumThreadWindows(int dwThreadId, EnumThreadDelegate lpfn, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public static void InspectProcess(int pid) {
        Process proc;
        try { proc = Process.GetProcessById(pid); }
        catch (Exception ex) { Console.WriteLine("Cannot get proc: " + ex.Message); return; }

        Console.WriteLine(string.Format("Process: {0} (PID {1}) Threads: {2}", proc.ProcessName, pid, proc.Threads.Count));

        int winCount = 0;
        foreach (ProcessThread thread in proc.Threads) {
            EnumThreadWindows(thread.Id, (hWnd, lParam) => {
                winCount++;
                RECT r = new RECT();
                GetWindowRect(hWnd, out r);
                RECT cr = new RECT();
                GetClientRect(hWnd, out cr);
                StringBuilder title = new StringBuilder(512);
                GetWindowText(hWnd, title, 512);
                StringBuilder cls = new StringBuilder(512);
                GetClassName(hWnd, cls, 512);
                bool vis = IsWindowVisible(hWnd);
                Console.WriteLine(string.Format("  Thread {0} | HWND: 0x{1:X} | Vis: {2} | Rect: ({3},{4})-({5},{6}) [{7}x{8}] | Client: [{9}x{10}] | Class: '{11}' | Title: '{12}'",
                    thread.Id, hWnd.ToInt64(), vis, r.Left, r.Top, r.Right, r.Bottom, r.Right - r.Left, r.Bottom - r.Top, cr.Right - cr.Left, cr.Bottom - cr.Top, cls.ToString(), title.ToString()));
                return true;
            }, IntPtr.Zero);
        }
        Console.WriteLine(string.Format("Total windows found for PID {0}: {1}", pid, winCount));
    }
}
"@

$msrdc = Get-Process msrdc -ErrorAction SilentlyContinue
if ($msrdc) {
    [MsrdcDeepInspector]::InspectProcess($msrdc.Id)
} else {
    Write-Host "msrdc is not running"
}
