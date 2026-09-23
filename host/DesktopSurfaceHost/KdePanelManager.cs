using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace NtPlasma.DesktopSurfaceHost
{
    public sealed class KdePanelManager
    {
        private const int GWL_STYLE = -16;
        private const int GWL_EXSTYLE = -20;
        private const int WS_EX_TOOLWINDOW = 0x00000080;
        private const int WS_EX_NOACTIVATE = 0x08000000;

        private static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
        private static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
        private static readonly IntPtr HWND_BOTTOM = new IntPtr(1);
        private const uint SWP_NOACTIVATE = 0x0010;
        private const uint SWP_SHOWWINDOW = 0x0040;
        private const uint SWP_FRAMECHANGED = 0x0020;
        private const uint SWP_NOSIZE = 0x0001;
        private const uint SWP_NOMOVE = 0x0002;

        private const long WS_POPUP = 0x80000000L;
        private const long WS_CHILD = 0x40000000L;
        private const long WS_CLIPSIBLINGS = 0x04000000L;
        private const long WS_CAPTION = 0x00C00000L;
        private const long WS_THICKFRAME = 0x00040000L;
        private const long WS_MINIMIZEBOX = 0x00020000L;
        private const long WS_MAXIMIZEBOX = 0x00010000L;
        private const long WS_SYSMENU = 0x00080000L;
        private const int WS_EX_APPWINDOW = 0x00040000;

        private const int SPI_GETWORKAREA = 0x0030;
        private const int SPI_SETWORKAREA = 0x002F;
        private const int SPIF_SENDCHANGE = 0x0002;

        [StructLayout(LayoutKind.Sequential)]
        public struct POINT
        {
            public int X, Y;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct RECT
        {
            public int Left, Top, Right, Bottom;
        }

        [DllImport("user32.dll")]
        private static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

        [DllImport("user32.dll")]
        private static extern bool SetThreadDesktop(IntPtr hDesktop);

        [DllImport("user32.dll")]
        private static extern bool CloseDesktop(IntPtr hDesktop);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr SetParent(IntPtr hWndChild, IntPtr hWndNewParent);

        [DllImport("user32.dll")]
        private static extern IntPtr GetParent(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool ScreenToClient(IntPtr hWnd, ref POINT lpPoint);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string? lpszClass, string? lpszWindow);

        [DllImport("user32.dll")]
        private static extern bool IsWindow(IntPtr hWnd);

        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpfn, IntPtr lParam);

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll")]
        private static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll")]
        private static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll")]
        private static extern IntPtr SetWindowLongPtr(IntPtr hWnd, int nIndex, IntPtr dwNewLong);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool SystemParametersInfo(int uiAction, int uiParam, ref RECT pvParam, int fWinIni);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        private readonly bool _hideExplorer;
        private CancellationTokenSource? _cts;

        private static bool _workAreaSet = false;
        private static readonly HashSet<IntPtr> _styledHwnds = new();
        private static readonly HashSet<IntPtr> _trackedPanelHwnds = new();
        private static volatile bool _isFullscreenActive = false;

        public static bool HasNativeDesktops { get; private set; }

        public static void SetFullscreenActive(bool active)
        {
            _isFullscreenActive = active;
            lock (_trackedPanelHwnds)
            {
                _trackedPanelHwnds.RemoveWhere(h => !IsWindow(h));
                foreach (var hwnd in _trackedPanelHwnds)
                {
                    if (active)
                    {
                        ShowWindow(hwnd, 0 /* SW_HIDE */);
                    }
                    else
                    {
                        ShowWindow(hwnd, 8 /* SW_SHOWNA */);
                        SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW);
                    }
                }
            }
        }

        public KdePanelManager(bool hideExplorer = false)
        {
            _hideExplorer = hideExplorer;
        }

        public void StartMonitoring()
        {
            _cts = new CancellationTokenSource();
            var token = _cts.Token;

            Task.Run(async () =>
            {
                while (!token.IsCancellationRequested)
                {
                    try
                    {
                        AlignPanels(_hideExplorer);
                    }
                    catch { }

                    await Task.Delay(1500, token);
                }
            }, token);
        }

        public void Stop()
        {
            _cts?.Cancel();
        }

        public static void FocusPrimaryDesktop()
        {
            IntPtr progman = FindWindowEx(IntPtr.Zero, IntPtr.Zero, "Progman", null);
            if (progman != IntPtr.Zero)
            {
                SetForegroundWindow(progman);
            }
        }

        public static void AlignPanels(bool hideExplorer = false)
        {
            var primary = Screen.PrimaryScreen;
            if (primary == null) return;

            // Keep Windows Explorer taskbars hidden ONLY if explicitly requested
            if (hideExplorer)
            {
                ExplorerHider.SetVisibility(false);
            }

            var desktopWindows = new List<(IntPtr Hwnd, string Title, int QrectX)>();
            var foundPanelHwnds = new List<IntPtr>();

            bool Callback(IntPtr hWnd, IntPtr lParam)
            {
                var classBuf = new StringBuilder(256);
                GetClassName(hWnd, classBuf, classBuf.Capacity);
                if (classBuf.ToString() != "RAIL_WINDOW")
                    return true;

                GetWindowThreadProcessId(hWnd, out uint pid);
                try
                {
                    var proc = Process.GetProcessById((int)pid);
                    if (!proc.ProcessName.Equals("msrdc", StringComparison.OrdinalIgnoreCase))
                        return true;
                }
                catch { return true; }

                var titleBuf = new StringBuilder(512);
                GetWindowText(hWnd, titleBuf, titleBuf.Capacity);
                string title = titleBuf.ToString();

                if (title.Contains("Desktop @", StringComparison.OrdinalIgnoreCase))
                {
                    var match = Regex.Match(title, @"QRect\(\s*(-?\d+)\s*,\s*(-?\d+)");
                    int qx = match.Success ? int.Parse(match.Groups[1].Value) : 0;
                    desktopWindows.Add((hWnd, title, qx));
                }
                else if ((title.IndexOf("Plasma", StringComparison.OrdinalIgnoreCase) >= 0 ||
                          title.IndexOf("plasmashell", StringComparison.OrdinalIgnoreCase) >= 0) &&
                         !title.Contains("Desktop @", StringComparison.OrdinalIgnoreCase))
                {
                    GetWindowRect(hWnd, out RECT r);
                    int w = r.Right - r.Left;
                    int h = r.Bottom - r.Top;
                    // Panel is horizontal across bottom: wide aspect ratio (w > h * 3) and at least 600px width
                    if (w > h * 3 && w >= 600)
                    {
                        foundPanelHwnds.Add(hWnd);
                    }
                }

                return true;
            }

            IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
            if (hDesk != IntPtr.Zero)
            {
                try
                {
                    EnumDesktopWindows(hDesk, Callback, IntPtr.Zero);
                }
                finally
                {
                    CloseDesktop(hDesk);
                }
            }

            if (desktopWindows.Count == 0 && foundPanelHwnds.Count == 0)
            {
                EnumWindows(Callback, IntPtr.Zero);
            }

            // 1. Hide any KDE Desktop background surfaces so Windows desktop wallpaper & icons remain active
            _styledHwnds.RemoveWhere(h => !IsWindow(h));

            if (desktopWindows.Count > 0)
            {
                foreach (var (hWnd, _, _) in desktopWindows)
                {
                    if (!_styledHwnds.Contains(hWnd))
                    {
                        ShowWindow(hWnd, 0 /* SW_HIDE */);
                        _styledHwnds.Add(hWnd);
                    }
                }
            }

            HasNativeDesktops = desktopWindows.Count > 0 || _styledHwnds.Count > 0;

            // 2. Dock KDE Panels / Taskbars to bottom of screens without mutating MSRDC window styles
            lock (_trackedPanelHwnds)
            {
                _trackedPanelHwnds.RemoveWhere(h => !IsWindow(h));
                foreach (var pHwnd in foundPanelHwnds)
                {
                    bool isNew = _trackedPanelHwnds.Add(pHwnd);

                    if (_isFullscreenActive)
                    {
                        ShowWindow(pHwnd, 0 /* SW_HIDE */);
                        continue;
                    }

                    GetWindowRect(pHwnd, out RECT r);
                    int panelH = r.Bottom - r.Top;
                    if (panelH <= 0 || panelH > 100) panelH = 48;
                    int desiredY = primary.Bounds.Bottom - panelH;
                    int desiredW = primary.Bounds.Width;
                    int desiredX = primary.Bounds.Left;

                    // Ensure the panel is firmly docked to the bottom of the screen.
                    // If MSRDC or Weston ever misplaces the panel (e.g. hovering halfway up the screen at Y=731),
                    // snap it down immediately to the screen bottom.
                    // Only invoke SetWindowPos if new or position/size differs, avoiding Z-order thrashing.
                    if (isNew || r.Top != desiredY || r.Left != desiredX || (r.Right - r.Left) != desiredW)
                    {
                        SetWindowPos(pHwnd, HWND_NOTOPMOST, desiredX, desiredY, desiredW, panelH,
                            SWP_NOACTIVATE | SWP_SHOWWINDOW);
                    }
                }
            }

            // Reserve workarea on primary screen ONLY ONCE (calling SPIF_SENDCHANGE in a loop causes monitor flicker)
            if (foundPanelHwnds.Count > 0 && !_workAreaSet)
            {
                var curWa = new RECT();
                SystemParametersInfo(SPI_GETWORKAREA, 0, ref curWa, 0);
                int desiredBottom = primary.Bounds.Bottom - 48;
                if (curWa.Bottom > desiredBottom)
                {
                    var newWa = new RECT
                    {
                        Left = primary.Bounds.Left,
                        Top = primary.Bounds.Top,
                        Right = primary.Bounds.Right,
                        Bottom = desiredBottom
                    };
                    SystemParametersInfo(SPI_SETWORKAREA, 0, ref newWa, SPIF_SENDCHANGE);
                }
                _workAreaSet = true;
            }
        }

    }
}
