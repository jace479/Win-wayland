$code = @"
using System;
using System.Runtime.InteropServices;

public static class RestoreExplorerHelper
{
    private const int SwShow = 5;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr FindWindowEx(IntPtr parentHandle, IntPtr childAfter, string className, string windowTitle);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    public static void Restore()
    {
        IntPtr primaryTray = FindWindow("Shell_TrayWnd", null);
        if (primaryTray != IntPtr.Zero)
        {
            ShowWindow(primaryTray, SwShow);
            Console.WriteLine("Shell_TrayWnd: " + primaryTray + ", Visible: " + IsWindowVisible(primaryTray));
        }

        IntPtr secondaryTray = IntPtr.Zero;
        while ((secondaryTray = FindWindowEx(IntPtr.Zero, secondaryTray, "Shell_SecondaryTrayWnd", null)) != IntPtr.Zero)
        {
            ShowWindow(secondaryTray, SwShow);
            Console.WriteLine("Shell_SecondaryTrayWnd: " + secondaryTray + ", Visible: " + IsWindowVisible(secondaryTray));
        }

        IntPtr progman = FindWindow("Progman", null);
        if (progman != IntPtr.Zero)
        {
            ShowWindow(progman, SwShow);
            Console.WriteLine("Progman: " + progman + ", Visible: " + IsWindowVisible(progman));
        }

        IntPtr workerW = IntPtr.Zero;
        while ((workerW = FindWindowEx(IntPtr.Zero, workerW, "WorkerW", null)) != IntPtr.Zero)
        {
            ShowWindow(workerW, SwShow);
            Console.WriteLine("WorkerW: " + workerW + ", Visible: " + IsWindowVisible(workerW));
        }
    }
}
"@

Add-Type -TypeDefinition $code -Language CSharp
[RestoreExplorerHelper]::Restore()
Write-Output "Explorer taskbars and desktop restored successfully."
