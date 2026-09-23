using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

namespace NtPlasma.DesktopSurfaceHost
{
    internal sealed class MultiMonitorDesktopManager
    {
        private const int SPIF_UPDATEINIFILE = 0x01;
        private const int SPIF_SENDCHANGE = 0x02;
        private const int SPI_SETDESKWALLPAPER = 0x0014;

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr FindWindow(string? lpClassName, string? lpWindowName);

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

        [DllImport("user32.dll")]
        private static extern bool CloseDesktop(IntPtr hDesktop);

        [DllImport("user32.dll")]
        private static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpfn, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
        private static extern bool SystemParametersInfo(int uAction, int uParam, string? lpvParam, int fuWinIni);

        [ComImport]
        [Guid("B92B56A9-8B55-4E14-9A89-0199BBB6F93B")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IDesktopWallpaper
        {
            void SetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string? monitorID, [MarshalAs(UnmanagedType.LPWStr)] string wallpaper);
            [return: MarshalAs(UnmanagedType.LPWStr)]
            string GetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string? monitorID);
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
        private struct RECT { public int Left, Top, Right, Bottom; }

        private enum DesktopWallpaperPosition { Center = 0, Tile = 1, Stretch = 2, Fit = 3, Fill = 4, Span = 5 }
        private enum DesktopSlideshowDirection { Forward = 0, Backward = 1 }

        [ComImport]
        [Guid("C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD")]
        private class DesktopWallpaperCoClass {}

        private string? _originalWallpaper = null;
        private System.Threading.Timer? _syncTimer = null;
        private string? _lastSyncedPath = null;

        public static IntPtr GetDesktopWorkerW()
        {
            IntPtr progman = FindWindow("Progman", null);
            if (progman != IntPtr.Zero)
            {
                ShowWindow(progman, 5 /* SW_SHOW */);
                return progman;
            }

            IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
            if (hDesk != IntPtr.Zero)
            {
                try
                {
                    EnumDesktopWindows(hDesk, (hWnd, lParam) =>
                    {
                        var sb = new StringBuilder(256);
                        GetClassName(hWnd, sb, sb.Capacity);
                        if (sb.ToString() == "Progman")
                        {
                            progman = hWnd;
                            return false;
                        }
                        return true;
                    }, IntPtr.Zero);
                }
                finally
                {
                    CloseDesktop(hDesk);
                }
            }

            return progman;
        }

        public void Start()
        {
            Console.WriteLine($"[ntKDE] MultiMonitorDesktopManager: Native desktop mode active (no dummy windows)");
            
            try
            {
                // Save original wallpaper so we can restore on clean exit
                SaveOriginalWallpaper();

                // Synchronize active KDE wallpaper to Windows desktop
                SyncKdeWallpaper();

                // Start periodic timer to detect wallpaper changes from KDE settings
                _syncTimer = new System.Threading.Timer(_ =>
                {
                    try { CheckAndSyncWallpaper(); } catch { }
                }, null, TimeSpan.FromSeconds(10), TimeSpan.FromSeconds(15));
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ntKDE] DesktopManager start warning: {ex.Message}");
            }
        }

        private void SaveOriginalWallpaper()
        {
            try
            {
                var dw = (IDesktopWallpaper)new DesktopWallpaperCoClass();
                _originalWallpaper = dw.GetWallpaper(null);
            }
            catch
            {
                try
                {
                    _originalWallpaper = Microsoft.Win32.Registry.GetValue(
                        @"HKEY_CURRENT_USER\Control Panel\Desktop", "Wallpaper", null) as string;
                }
                catch { }
            }
        }

        public void SetSurfacesVisible(bool visible)
        {
            // No-op: Dummy desktop windows disabled per design requirements.
        }

        public void Stop()
        {
            _syncTimer?.Dispose();
            _syncTimer = null;

            try
            {
                if (!string.IsNullOrEmpty(_originalWallpaper) && File.Exists(_originalWallpaper))
                {
                    ApplyWallpaperToAllMonitors(_originalWallpaper);
                }
                else
                {
                    SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, null, SPIF_SENDCHANGE);
                }
            }
            catch { }
        }

        public static void SyncKdeWallpaper()
        {
            string? wallpaperFile = ResolveKdeWallpaperFile();
            if (string.IsNullOrEmpty(wallpaperFile) || !File.Exists(wallpaperFile))
            {
                Console.WriteLine("[ntKDE] Wallpaper: Could not resolve active KDE wallpaper image.");
                return;
            }

            string targetDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "nt-plasma");
            Directory.CreateDirectory(targetDir);
            string targetFile = Path.Combine(targetDir, "wallpaper.jpg");

            try
            {
                File.Copy(wallpaperFile, targetFile, true);
                ApplyWallpaperToAllMonitors(targetFile);
                Console.WriteLine($"[ntKDE] ✓ Applied KDE desktop background: {targetFile}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ntKDE] Error applying KDE wallpaper: {ex.Message}");
            }
        }

        private void CheckAndSyncWallpaper()
        {
            string? wallpaperFile = ResolveKdeWallpaperFile();
            if (!string.IsNullOrEmpty(wallpaperFile) && wallpaperFile != _lastSyncedPath)
            {
                SyncKdeWallpaper();
                _lastSyncedPath = wallpaperFile;
            }
        }

        public static string? ResolveKdeWallpaperFile()
        {
            string distro = "Ubuntu";
            string uncBase = $@"\\wsl.localhost\{distro}";

            // 1. Try reading ~/.config/plasma-org.kde.plasma.desktop-appletsrc
            string userHome = $@"\\wsl.localhost\{distro}\home\jace479";
            string appletsrc = Path.Combine(userHome, ".config", "plasma-org.kde.plasma.desktop-appletsrc");

            string? rawImageVal = null;
            if (File.Exists(appletsrc))
            {
                try
                {
                    foreach (var line in File.ReadLines(appletsrc))
                    {
                        if (line.StartsWith("Image=", StringComparison.OrdinalIgnoreCase))
                        {
                            rawImageVal = line.Substring(6).Trim();
                            break;
                        }
                    }
                }
                catch { }
            }

            if (!string.IsNullOrEmpty(rawImageVal))
            {
                if (rawImageVal.StartsWith("file://", StringComparison.OrdinalIgnoreCase))
                {
                    rawImageVal = rawImageVal.Substring(7);
                }

                string uncPath = Path.Combine(uncBase, rawImageVal.TrimStart('/', '\\').Replace('/', '\\'));
                if (Directory.Exists(uncPath))
                {
                    // Check contents/images_dark or contents/images
                    string darkDir = Path.Combine(uncPath, "contents", "images_dark");
                    string lightDir = Path.Combine(uncPath, "contents", "images");

                    string chosenDir = Directory.Exists(darkDir) ? darkDir : lightDir;
                    if (Directory.Exists(chosenDir))
                    {
                        var files = Directory.GetFiles(chosenDir, "*.jpg")
                            .OrderByDescending(f => new FileInfo(f).Length)
                            .ToList();
                        if (files.Count > 0) return files[0];
                    }
                }
                else if (File.Exists(uncPath))
                {
                    return uncPath;
                }
            }

            // Fallback to standard Flow dark/light wallpaper
            string flowDark = Path.Combine(uncBase, @"usr\share\wallpapers\Flow\contents\images_dark\5120x2880.jpg");
            if (File.Exists(flowDark)) return flowDark;

            string flowLight = Path.Combine(uncBase, @"usr\share\wallpapers\Flow\contents\images\5120x2880.jpg");
            if (File.Exists(flowLight)) return flowLight;

            // Fallback to cached wallpaper if exists
            string cached = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "nt-plasma", "wallpaper.jpg");
            if (File.Exists(cached)) return cached;

            return null;
        }

        public static void ApplyWallpaperToAllMonitors(string imagePath)
        {
            try
            {
                var dw = (IDesktopWallpaper)new DesktopWallpaperCoClass();
                uint count = dw.GetMonitorDevicePathCount();
                for (uint i = 0; i < count; i++)
                {
                    string monId = dw.GetMonitorDevicePathAt(i);
                    dw.SetWallpaper(monId, imagePath);
                }
                dw.SetWallpaper(null, imagePath);
                dw.SetPosition(DesktopWallpaperPosition.Fill);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ntKDE] IDesktopWallpaper notice: {ex.Message}");
            }

            try
            {
                SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, imagePath, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);
            }
            catch { }
        }
    }
}
