$code = @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public static class RailWindowFinder
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

    public static string[] ListRailWindows()
    {
        var list = new System.Collections.Generic.List<string>();
        EnumWindows((hWnd, lParam) =>
        {
            var classBuf = new StringBuilder(256);
            GetClassName(hWnd, classBuf, 256);
            string cls = classBuf.ToString();

            if (cls.Contains("RAIL_WINDOW") || cls.Contains("Weston") || cls.Contains("KDE") || cls.Contains("mstsc"))
            {
                var titleBuf = new StringBuilder(512);
                GetWindowText(hWnd, titleBuf, 512);
                bool visible = IsWindowVisible(hWnd);
                list.Add("HWND: " + hWnd + " | Class: " + cls + " | Visible: " + visible + " | Title: '" + titleBuf.ToString() + "'");
            }
            return true;
        }, IntPtr.Zero);
        return list.ToArray();
    }
}
"@

Add-Type -TypeDefinition $code -Language CSharp
[RailWindowFinder]::ListRailWindows()
