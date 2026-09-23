using System;
using System.Runtime.InteropServices;

[ComImport]
[Guid("B92B56A9-8B55-4E14-9A89-0199BBB6F93B")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IDesktopWallpaper
{
    void SetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string monitorID, [MarshalAs(UnmanagedType.LPWStr)] string wallpaper);
    [return: MarshalAs(UnmanagedType.LPWStr)]
    string GetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string monitorID);
    [return: MarshalAs(UnmanagedType.LPWStr)]
    string GetMonitorDevicePathAt(uint monitorIndex);
    uint GetMonitorDevicePathCount();
    void GetMonitorRECT([MarshalAs(UnmanagedType.LPWStr)] string monitorID, out RECT displayRect);
    void SetBackgroundColor(uint color);
    uint GetBackgroundColor();
    void SetPosition(DesktopWallpaperPosition position);
    DesktopWallpaperPosition GetPosition();
    void SetSlideshow(IntPtr items);
    IntPtr GetSlideshow();
    void AdvanceSlideshow([MarshalAs(UnmanagedType.LPWStr)] string monitorID, DesktopSlideshowDirection direction);
    DesktopSlideshowDirection GetStatus();
    bool Enable();
}

[StructLayout(LayoutKind.Sequential)]
public struct RECT { public int Left, Top, Right, Bottom; }

public enum DesktopWallpaperPosition { Center = 0, Tile = 1, Stretch = 2, Fit = 3, Fill = 4, Span = 5 }
public enum DesktopSlideshowDirection { Forward = 0, Backward = 1 }

[ComImport]
[Guid("C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD")]
public class DesktopWallpaperCoClass {}

public class WallpaperApplier
{
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern bool SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);

    [STAThread]
    public static void Main(string[] args)
    {
        string path = args.Length > 0 ? args[0] : "";
        if (string.IsNullOrEmpty(path))
        {
            Console.WriteLine("No wallpaper path provided.");
            return;
        }

        Console.WriteLine("Applying wallpaper: " + path);
        try
        {
            var dw = (IDesktopWallpaper)new DesktopWallpaperCoClass();
            uint count = dw.GetMonitorDevicePathCount();
            Console.WriteLine("IDesktopWallpaper monitor count: " + count);
            for (uint i = 0; i < count; i++)
            {
                string monId = dw.GetMonitorDevicePathAt(i);
                Console.WriteLine("Setting monitor " + i + " (" + monId + ")...");
                dw.SetWallpaper(monId, path);
            }
            dw.SetWallpaper(null, path);
            dw.SetPosition(DesktopWallpaperPosition.Fill);
            Console.WriteLine("IDesktopWallpaper applied successfully!");
        }
        catch (Exception ex)
        {
            Console.WriteLine("IDesktopWallpaper error: " + ex.ToString());
        }

        try
        {
            SystemParametersInfo(0x0014 /* SPI_SETDESKWALLPAPER */, 0, path, 0x01 | 0x02);
            Console.WriteLine("SystemParametersInfo applied successfully.");
        }
        catch (Exception ex)
        {
            Console.WriteLine("SystemParametersInfo error: " + ex.Message);
        }
    }
}
