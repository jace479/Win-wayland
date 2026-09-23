Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;

public class WinLister {
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

    public static void ListAll() {
        EnumWindows((hWnd, lParam) => {
            if (!IsWindowVisible(hWnd)) return true;

            var title = new StringBuilder(512);
            GetWindowText(hWnd, title, 512);
            var cls = new StringBuilder(512);
            GetClassName(hWnd, cls, 512);

            string sTitle = title.ToString();
            string sCls = cls.ToString();

            if (string.IsNullOrEmpty(sTitle)) return true;

            uint pid = 0;
            GetWindowThreadProcessId(hWnd, out pid);
            long style = GetWindowLongPtr(hWnd, -16).ToInt64();

            Console.WriteLine(string.Format("HWND=0x{0:X8} | PID={1,6} | Style=0x{2:X8} | Class={3,-25} | Title={4}", 
                hWnd.ToInt64(), pid, style, sCls, sTitle));
            return true;
        }, IntPtr.Zero);
    }
}
'@

[WinLister]::ListAll()
