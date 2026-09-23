Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public class WinList
{
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);
    [DllImport("user32.dll")]
    private static extern bool SetThreadDesktop(IntPtr hDesktop);

    public static List<string> GetAll()
    {
        IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
        if (hDesk != IntPtr.Zero) { SetThreadDesktop(hDesk); }

        var res = new List<string>();
        EnumWindows((h, l) => {
            if (IsWindowVisible(h))
            {
                var sbT = new StringBuilder(256);
                var sbC = new StringBuilder(256);
                GetWindowText(h, sbT, 256);
                GetClassName(h, sbC, 256);
                if (sbT.Length > 0)
                {
                    res.Add(string.Format("{0:X8} | {1} | {2}", h.ToInt64(), sbC.ToString(), sbT.ToString()));
                }
            }
            return true;
        }, IntPtr.Zero);
        return res;
    }
}
"@

[WinList]::GetAll()
