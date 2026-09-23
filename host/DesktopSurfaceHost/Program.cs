using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

namespace NtPlasma.DesktopSurfaceHost;

internal static class Program
{
    [DllImport("kernel32.dll")]
    private static extern nint GetConsoleWindow();

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(nint hWnd, int nCmdShow);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern nint OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll")]
    private static extern bool SetThreadDesktop(nint hDesktop);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool SystemParametersInfo(int uiAction, int uiParam, ref KdePanelManager.RECT pvParam, int fWinIni);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    private static extern bool SystemParametersInfo(int uiAction, int uiParam, string? pvParam, int fWinIni);

    [DllImport("kernel32.dll")]
    private static extern bool SetConsoleCtrlHandler(ConsoleCtrlDelegate handler, bool add);
    private delegate bool ConsoleCtrlDelegate(int ctrlType);
    private static ConsoleCtrlDelegate? _consoleCtrlHandler;

    private static int _cleanUpDone = 0;
    private static bool _ownsSession = false;

    public static void Cleanup(bool fromCtrlC = false)
    {
        if (!_ownsSession && !fromCtrlC) return;
        if (Interlocked.Exchange(ref _cleanUpDone, 1) != 0) return;

        try
        {
            Console.WriteLine("[ntKDE] Restoring Windows Explorer...");
            ExplorerHider.SetVisibility(true);
            SystemParametersInfo(0x0014 /* SPI_SETDESKWALLPAPER */, 0, null, 0x0002 /* SPIF_SENDCHANGE */);
        }
        catch { }


        try
        {
            if (Screen.PrimaryScreen != null)
            {
                var primaryBounds = Screen.PrimaryScreen.Bounds;
                var fullWa = new KdePanelManager.RECT
                {
                    Left = primaryBounds.Left,
                    Top = primaryBounds.Top,
                    Right = primaryBounds.Right,
                    Bottom = primaryBounds.Bottom
                };
                SystemParametersInfo(0x002F /* SPI_SETWORKAREA */, 0, ref fullWa, 0x0002 /* SPIF_SENDCHANGE */);
            }
        }
        catch { }

        try
        {
            var repoRoot = FindRepoRoot();
            var stopScript = ConvertToWslPath(Path.Combine(repoRoot, "wsl", "stop-nested-plasma.sh"));
            var psi = new ProcessStartInfo("wsl.exe", $"-d Ubuntu -u jace479 -e bash \"{stopScript}\"")
            {
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            using var proc = Process.Start(psi);
            proc?.WaitForExit(6000);
        }
        catch { }
    }

    private static void AttachToDefaultDesktop()
    {
        try
        {
            var hDesktop = OpenDesktop("default", 0, false, 0x01FF);
            if (hDesktop != nint.Zero)
            {
                SetThreadDesktop(hDesktop);
            }
        }
        catch { }
    }

    [STAThread]
    private static void Main(string[] args)
    {
        // Install global unhandled exception handler for crash diagnostics
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
        {
            if (e.ExceptionObject is Exception ex)
            {
                DiagnosticLog.Fatal("Unhandled exception", ex);
            }
        };

        // Automatically run cleanup whenever the command ends, terminal closes, or Ctrl+C is pressed
        _consoleCtrlHandler = ctrlType =>
        {
            Cleanup(fromCtrlC: true);
            return false;
        };
        try { SetConsoleCtrlHandler(_consoleCtrlHandler, true); } catch { }

        try
        {
            Console.CancelKeyPress += (_, e) =>
            {
                e.Cancel = true;
                Cleanup(fromCtrlC: true);
                Environment.Exit(0);
            };
        }
        catch { }

        AppDomain.CurrentDomain.ProcessExit += (_, _) =>
        {
            Cleanup();
        };

        AttachToDefaultDesktop();
        try
        {
            var command = args.Length > 0 ? args[0].ToLowerInvariant() : "desktop";

            switch (command)
            {
                case "--help":
                case "-h":
                case "help":
                    PrintHelp();
                    return;

                case "status":
                    HandleStatus();
                    return;

                case "shell":
                    HandleShell(args);
                    return;

                case "restore":
                case "unhide":
                    ExplorerHider.SetVisibility(true);
                    DiagnosticLog.Info("Windows Explorer taskbars and desktop set to visible.");
                    return;

                case "sync":
                    HandleSync();
                    return;

                case "stop":
                case "kill":
                case "quit":
                case "exit":
                    HandleStop();
                    return;

                case "notify":
                    HandleNotify(args);
                    return;

                case "volume":
                    HandleVolume(args);
                    return;

                case "app":
                    HandleApp(args);
                    return;

                case "compose":
                case "-c":
                    HandleCompose(args);
                    return;

                case "windows":
                case "find":
                    HandleListWindows();
                    return;

                case "align":
                    KdePanelManager.AlignPanels(hideExplorer: false);
                    DiagnosticLog.Info($"AlignPanels completed. HasNativeDesktops: {KdePanelManager.HasNativeDesktops}");
                    return;

                case "tray":
                    HandleTray();
                    return;

                case "wallpaper":
                case "bg":
                    MultiMonitorDesktopManager.SyncKdeWallpaper();
                    return;

                case "desktop":
                case "preview":
                default:
                    HandleDesktop(args);
                    break;
            }
        }
        catch (Exception error)
        {
            DiagnosticLog.Fatal("Unhandled error in Main", error);
        }
    }

    private static void PrintHelp()
    {
        Console.WriteLine("""

========================================================================
 ntKDE - Hybrid KDE Plasma Desktop Environment for Windows NT
========================================================================

Usage:
  ntkde [command] [options]

Commands:
  desktop [options]           Launch authentic KDE Plasma Desktop Surface (default)
                              Options: --span, --hide-explorer, --windowed
  wallpaper, bg               Synchronize active KDE Plasma wallpaper to Windows across all monitors
  kill, stop                  Cleanly kill ntKDE, terminate WSL Plasma session, and restore Explorer
  restore                     Unhide Windows Explorer taskbars and desktop icons immediately
  tray                        Start ntKDE Tray & Session Controller without auto-launch
  app <appName> [args...]     Launch a KDE application natively (dolphin, konsole, krunner, systemsettings)
  compose <processName>       Start Path B native window composition for an app
  sync                        Scan and sync Windows Win32/UWP apps & icons to KDE
  shell [--set | --restore]   Configure or revert Winlogon Shell replacement
  status                      Display diagnostic health report of WSL, D3D, and Shell
  help                        Show this help text

Global Hotkeys (active while ntKDE is running):
  Alt + Space                 Launch / focus KRunner quick launcher
  Win + T                     Launch Konsole terminal
  Win + E                     Launch Dolphin file manager
  Ctrl+Alt+Shift+Esc          Emergency Recovery: restore Explorer and exit ntKDE

Examples:
  ntkde                       Launch KDE Plasma desktop on primary monitor
  ntkde desktop --span        Launch KDE Plasma spanning across all monitors
  ntkde app dolphin           Launch Dolphin file manager with Windows places
  ntkde compose notepad       Compose Notepad inside KDE Breeze styling
  ntkde status                Show system status report

""");
    }

    private static void HandleStatus()
    {
        Console.WriteLine();
        Console.WriteLine("=================================================");
        Console.WriteLine(" ntKDE System & Integration Status");
        Console.WriteLine("=================================================");
        Console.WriteLine($"Host OS:         {Environment.OSVersion}");
        Console.WriteLine($"Winlogon Shell:  {ShellRegistry.GetCurrentShell()}");
        Console.WriteLine($"WSL Status:      {WslSessionProbe.GetStatus()}");
        Console.WriteLine($"Direct3D 12:     {Direct3D12Probe.Describe()}");
        Console.WriteLine($"Direct3D 11On12: {D3D11On12Probe.Describe()}");
        if (D3D11DeviceBridge.TryCreate(out var d3dBridge))
        {
            Console.WriteLine($"Direct3D 11:     D3D11: hardware device available (Feature Level 0x{d3dBridge?.FeatureLevel:X})");
            d3dBridge?.Dispose();
        }
        else
        {
            Console.WriteLine("Direct3D 11:     D3D11: unavailable");
        }
        Console.WriteLine($"Capture Interop: {(GraphicsCaptureInterop.IsAvailable() ? "Available" : "Unavailable")}");
        Console.WriteLine($"Frame Pool:      {(GraphicsCaptureInterop.IsFramePoolAvailable() ? "Available" : "Unavailable")}");

        var primary = Screen.PrimaryScreen;
        Console.WriteLine($"Primary Display: {primary?.Bounds.Width}x{primary?.Bounds.Height} at ({primary?.Bounds.X},{primary?.Bounds.Y})");
        Console.WriteLine($"Total Displays:  {Screen.AllScreens.Length}");
        Console.WriteLine("=================================================");
        Console.WriteLine();
    }

    private static void HandleShell(string[] args)
    {
        if (args.Length > 1 && (args[1] is "--restore" or "restore" or "-r"))
        {
            ShellRegistry.RestoreShell();
            Console.WriteLine("[ntKDE] Restored Windows shell to default (explorer.exe).");
        }
        else if (args.Length > 1 && (args[1] is "--set" or "set" or "-s"))
        {
            var exePath = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName;
            if (!string.IsNullOrEmpty(exePath))
            {
                ShellRegistry.SetShell(exePath);
                Console.WriteLine($"[ntKDE] Configured ntKDE as Winlogon Shell: {exePath}");
                Console.WriteLine("[ntKDE] To restore Explorer at any time: ntkde shell --restore");
            }
        }
        else
        {
            Console.WriteLine($"[ntKDE] Current Winlogon Shell: {ShellRegistry.GetCurrentShell()}");
            Console.WriteLine("Usage: ntkde shell [--set | --restore]");
        }
    }

    public static void HandleSync()
    {
        var repoRoot = FindRepoRoot();
        var syncScript = Path.Combine(repoRoot, "powershell", "Sync-WindowsAppsToKde.ps1");
        DiagnosticLog.Info("Synchronizing Windows applications and icons to KDE...");
        var psi = new ProcessStartInfo("powershell.exe", $"-NoProfile -ExecutionPolicy Bypass -File \"{syncScript}\" -DistroName Ubuntu")
        {
            UseShellExecute = false,
        };
        using var proc = Process.Start(psi);
        proc?.WaitForExit();
    }

    public static void HandleStop()
    {
        Console.WriteLine("[ntKDE] Stopping ntKDE and restoring Windows desktop environment...");
        Cleanup();

        // 4. Kill other host ntkde / DesktopSurfaceHost processes
        try
        {
            var currentPid = Environment.ProcessId;
            var otherProcesses = Process.GetProcessesByName("ntkde")
                .Concat(Process.GetProcessesByName("DesktopSurfaceHost"))
                .Where(p => p.Id != currentPid)
                .GroupBy(p => p.Id)
                .Select(g => g.First())
                .ToList();

            int killedCount = 0;
            foreach (var p in otherProcesses)
            {
                try
                {
                    p.Kill();
                    killedCount++;
                }
                catch { }
            }
            if (killedCount > 0)
            {
                Console.WriteLine($"[ntKDE] ✓ Terminated {killedCount} running ntKDE host process(es).");
            }
        }
        catch { }

        Console.WriteLine("[ntKDE] ntKDE has been completely stopped.");
    }

    public static void HandleApp(string[] args)
    {
        var appName = args.Length > 1 ? args[1] : "dolphin";
        var appArgs = args.Length > 2 ? string.Join(" ", args.Skip(2).Select(a => $"\"{a}\"")) : "";
        var repoRoot = FindRepoRoot();
        var launchScript = ConvertToWslPath(Path.Combine(repoRoot, "wsl", "launch-app.sh"));

        DiagnosticLog.Info($"Launching KDE app '{appName}' in WSL...");
        Process.Start(new ProcessStartInfo("wsl.exe", $"-d Ubuntu -u jace479 -e bash \"{launchScript}\" {appName} {appArgs}")
        {
            UseShellExecute = false,
            CreateNoWindow = true,
        });
    }

    public static void HandleNotify(string[] args)
    {
        var title = args.Length > 1 ? args[1] : "ntKDE Notification";
        var body = args.Length > 2 ? string.Join(" ", args.Skip(2)) : "";
        if (NotificationBridge.Instance != null)
        {
            NotificationBridge.Instance.Notify(title, body);
        }
        else
        {
            var script = "import os, subprocess, glob\n" +
                "for p in glob.glob('/proc/[0-9]*/environ'):\n" +
                "    try:\n" +
                "        with open(p, 'rb') as f:\n" +
                "            e = f.read().decode('latin1').split('\\0')\n" +
                "        for v in e:\n" +
                "            if v.startswith('DBUS_SESSION_BUS_ADDRESS='):\n" +
                "                os.environ['DBUS_SESSION_BUS_ADDRESS'] = v.split('=', 1)[1]\n" +
                "                break\n" +
                "    except: pass\n" +
                $"subprocess.Popen(['gdbus','call','--session','--dest','org.freedesktop.Notifications','--object-path','/org/freedesktop/Notifications','--method','org.freedesktop.Notifications.Notify','Windows','0','preferences-desktop-notification',r'''{title}''',r'''{body}''','[]','{{}}','5000'])";
            Process.Start(new ProcessStartInfo("wsl.exe", $"-d Ubuntu -u jace479 python3 -c \"{script.Replace("\"", "\\\"")}\"")
            {
                UseShellExecute = false,
                CreateNoWindow = true,
            });
        }
        Console.WriteLine($"[ntKDE] Dispatched notification: '{title}' - '{body}'");
    }

    public static void HandleVolume(string[] args)
    {
        using var audio = new AudioVolumeBridge();
        var sub = args.Length > 1 ? args[1].ToLowerInvariant() : "get";
        switch (sub)
        {
            case "up":
                audio.VolumeUp();
                Console.WriteLine($"[ntKDE] Volume: {(int)(audio.GetMasterVolume() * 100)}%");
                break;
            case "down":
                audio.VolumeDown();
                Console.WriteLine($"[ntKDE] Volume: {(int)(audio.GetMasterVolume() * 100)}%");
                break;
            case "mute":
                audio.ToggleMute();
                Console.WriteLine($"[ntKDE] Muted: {audio.IsMuted()}");
                break;
            case "play":
            case "pause":
            case "playpause":
                AudioVolumeBridge.PlayPause();
                Console.WriteLine("[ntKDE] Media: Play/Pause toggled");
                break;
            case "next":
                AudioVolumeBridge.NextTrack();
                Console.WriteLine("[ntKDE] Media: Next track");
                break;
            case "prev":
                AudioVolumeBridge.PreviousTrack();
                Console.WriteLine("[ntKDE] Media: Previous track");
                break;
            default:
                if (float.TryParse(sub, out var level))
                {
                    if (level > 1.0f) level /= 100.0f;
                    audio.SetMasterVolume(level);
                }
                Console.WriteLine($"[ntKDE] Current Volume: {(int)(audio.GetMasterVolume() * 100)}% (Muted: {audio.IsMuted()})");
                break;
        }
    }

    public static void StartDesktopSession(int width, int height)
    {
        // Pre-flight WSL health check
        DiagnosticLog.Info("Running WSL health gate before desktop session launch...");
        var health = WslHealthGate.Check();
        if (!health.IsReady)
        {
            DiagnosticLog.Warn($"WSL health gate failed: {health.FailureReason}");
            DiagnosticLog.Warn("Desktop session will start in degraded mode.");
            return;
        }

        DiagnosticLog.Info($"WSL health gate passed (Flavor={health.DesktopFlavor}, Plasma={health.PlasmaInstalled}, CoreApps={health.CoreAppsInstalled}, X11={health.X11Available}).");

        var repoRoot = FindRepoRoot();

        // Asynchronously sync Windows apps to KDE Kickoff start menu
        Task.Run(() =>
        {
            try
            {
                var syncScript = Path.Combine(repoRoot, "powershell", "Sync-WindowsAppsToKde.ps1");
                if (File.Exists(syncScript))
                {
                    using var p = Process.Start(new ProcessStartInfo("powershell.exe",
                        $"-NoProfile -ExecutionPolicy Bypass -File \"{syncScript}\" -DistroName Ubuntu")
                    {
                        UseShellExecute = false,
                        CreateNoWindow = true,
                    });
                    p?.WaitForExit(20000);
                }
            }
            catch (Exception ex)
            {
                DiagnosticLog.Error("Sync", "Background app sync failed", ex);
            }
        });

        var startScript = ConvertToWslPath(Path.Combine(repoRoot, "wsl", "start-panels.sh"));
        DiagnosticLog.Info($"Starting KDE Plasma Desktop session in WSL...");
        Process.Start(new ProcessStartInfo("wsl.exe", $"-d Ubuntu -u jace479 bash \"{startScript}\" {width} {height}")
        {
            UseShellExecute = false,
            CreateNoWindow = true,
        });
    }

    private static void HandleDesktop(string[] args)
    {
        var span = args.Any(a => a.Equals("--span", StringComparison.OrdinalIgnoreCase));
        var hideExplorer = !args.Any(a => a.Equals("--keep-explorer", StringComparison.OrdinalIgnoreCase) ||
                                          a.Equals("--show-explorer", StringComparison.OrdinalIgnoreCase));
        var borderless = !args.Any(a => a.Equals("--windowed", StringComparison.OrdinalIgnoreCase));

        var targetBounds = span
            ? SystemInformation.VirtualScreen
            : (Screen.PrimaryScreen?.Bounds ?? new Rectangle(0, 0, 1920, 1080));

        using var singleInstanceMutex = new Mutex(true, "NtKde_Desktop_Session_Mutex", out bool isNewInstance);
        if (!isNewInstance)
        {
            Console.WriteLine("[ntKDE] An ntKDE desktop session is already running.");
            Console.WriteLine("[ntKDE] Use 'ntkde kill' to stop the running session.");
            return;
        }
        _ownsSession = true;

        // Initialize WinForms subsystem (visual styles, text rendering, DPI)
        // MUST happen before any Form/IWin32Window is created
        ApplicationConfiguration.Initialize();

        // Start session in WSL (using combined virtual screen size)
        StartDesktopSession(targetBounds.Width, targetBounds.Height);

        // Hide console window if launched from Explorer GUI (no visible console output needed)
        var consoleWnd = GetConsoleWindow();
        if (consoleWnd != nint.Zero && !Debugger.IsAttached && args.Length == 0)
        {
            ShowWindow(consoleWnd, 0);
        }

        var panelMgr = new KdePanelManager(hideExplorer);
        panelMgr.StartMonitoring();

        var desktopMgr = new MultiMonitorDesktopManager();
        desktopMgr.Start();

        try
        {
            if (hideExplorer)
            {
                ExplorerHider.SetVisibility(false);
            }

            using var context = new NtKdeTrayContext(targetBounds, borderless, hideExplorer, desktopMgr);
            Application.Run(context);
        }
        finally
        {
            desktopMgr.Stop();
            panelMgr.Stop();
            Cleanup();
            if (consoleWnd != nint.Zero)
            {
                ShowWindow(consoleWnd, 5);
            }
        }
    }

    private static void HandleTray()
    {
        var primaryBounds = Screen.PrimaryScreen?.Bounds ?? new Rectangle(0, 0, 1920, 1080);
        ApplicationConfiguration.Initialize();
        using var context = new NtKdeTrayContext(primaryBounds, borderless: false, hideExplorer: false);
        Application.Run(context);
    }

    private static void HandleCompose(string[] args)
    {
        if (args.Any(a => a.Equals("--list", StringComparison.OrdinalIgnoreCase) || a.Equals("-l", StringComparison.OrdinalIgnoreCase)))
        {
            var windows = WindowsTaskTracker.EnumerateComposableWindows();
            Console.WriteLine($"[ntKDE] Discovered {windows.Count} composable top-level windows:");
            Console.WriteLine(string.Format("{0,-12} {1,-8} {2,-20} {3}", "HWND", "PID", "PROCESS", "TITLE"));
            Console.WriteLine(new string('-', 75));
            foreach (var win in windows)
            {
                Console.WriteLine(string.Format("0x{0,-10:X} {1,-8} {2,-20} {3}", (long)win.Hwnd, win.Pid, win.ProcessName, win.Title));
            }
            return;
        }

        var targetArg = args.Skip(1).FirstOrDefault(a => !a.StartsWith("-")) ?? "notepad";
        var hostOnly = args.Any(a => a.Equals("--host-only", StringComparison.OrdinalIgnoreCase) ||
                                     a.Equals("--no-wsl", StringComparison.OrdinalIgnoreCase) ||
                                     a.Equals("--streamer-only", StringComparison.OrdinalIgnoreCase));
        var repoRoot = FindRepoRoot();
        var presenterPath = ConvertToWslPath(Path.Combine(repoRoot, "wsl", "foreign_window_presenter.py"));

        nint targetHwnd = nint.Zero;
        string targetDisplayName = targetArg;
        string normalizedName = Path.GetFileNameWithoutExtension(targetArg);

        // 1. Check if targetArg is an HWND in hex or decimal
        if (targetArg.StartsWith("0x", StringComparison.OrdinalIgnoreCase) &&
            long.TryParse(targetArg[2..], System.Globalization.NumberStyles.HexNumber, null, out var hexVal))
        {
            targetHwnd = (nint)hexVal;
        }
        else if (long.TryParse(targetArg, out var decVal) && decVal > 0x1000)
        {
            targetHwnd = (nint)decVal;
        }

        // 2. If not a direct HWND, look up among composable windows by process name or title
        if (targetHwnd == nint.Zero)
        {
            var disc = NativeWindowDiscovery.Find(targetArg);
            targetHwnd = disc.Windows.FirstOrDefault();

            if (targetHwnd == nint.Zero)
            {
                var activeWindows = WindowsTaskTracker.EnumerateComposableWindows();
                var matched = activeWindows.FirstOrDefault(w =>
                    string.Equals(w.ProcessName, normalizedName, StringComparison.OrdinalIgnoreCase) ||
                    w.Title.Contains(targetArg, StringComparison.OrdinalIgnoreCase));

                if (matched != null)
                {
                    targetHwnd = matched.Hwnd;
                    targetDisplayName = matched.Title;
                    normalizedName = matched.ProcessName;
                }
            }
        }

        // 3. If still not found, try to launch the process and wait for its window
        if (targetHwnd == nint.Zero && Process.GetProcessesByName(normalizedName).Length == 0)
        {
            try
            {
                Process.Start(new ProcessStartInfo(targetArg) { UseShellExecute = true });
                Thread.Sleep(800);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ntKDE] Failed to start process '{targetArg}': {ex.Message}");
            }
        }

        if (targetHwnd == nint.Zero)
        {
            Console.WriteLine($"[ntKDE] Searching for visible window for '{targetArg}'...");
            for (var i = 0; i < 20 && targetHwnd == nint.Zero; i++)
            {
                Thread.Sleep(300);
                var disc = NativeWindowDiscovery.Find(targetArg);
                targetHwnd = disc.Windows.FirstOrDefault();
                if (targetHwnd == nint.Zero)
                {
                    var activeWindows = WindowsTaskTracker.EnumerateComposableWindows();
                    var matched = activeWindows.FirstOrDefault(w =>
                        string.Equals(w.ProcessName, normalizedName, StringComparison.OrdinalIgnoreCase) ||
                        w.Title.Contains(targetArg, StringComparison.OrdinalIgnoreCase));
                    if (matched != null)
                    {
                        targetHwnd = matched.Hwnd;
                        targetDisplayName = matched.Title;
                        normalizedName = matched.ProcessName;
                    }
                }
            }
        }

        if (targetHwnd == nint.Zero)
        {
            Console.WriteLine($"[ntKDE] Error: could not discover window for '{targetArg}'. Use 'ntkde compose --list' to see available windows.");
            return;
        }

        Console.WriteLine($"[ntKDE] Discovered HWND 0x{targetHwnd:X} for '{targetDisplayName}'.");
        Console.WriteLine($"[ntKDE] Initializing Path B Zero-TCP Capture Streamer...");
        using var streamer = new WindowCaptureStreamer();
        streamer.Start(targetHwnd);

        if (hostOnly)
        {
            var pipeName = "ntkde_surface_" + normalizedName;
            Console.WriteLine($"[ntKDE] Host-only mode active. Serving Windows Named Pipe \\\\.\\pipe\\{pipeName}. Press Ctrl+C to exit.");
            streamer.StartNamedPipeServer(pipeName);
            using var exitEvent = new ManualResetEventSlim(false);
            Console.CancelKeyPress += (_, e) =>
            {
                e.Cancel = true;
                exitEvent.Set();
            };
            exitEvent.Wait();
            return;
        }

        var verifyArg = "";
        for (var i = 0; i < args.Length; i++)
        {
            if (args[i].Equals("--verify-frames", StringComparison.OrdinalIgnoreCase) && i + 1 < args.Length)
            {
                verifyArg = $"--verify-frames {args[i + 1]}";
                break;
            }
            if (args[i].Equals("--verify", StringComparison.OrdinalIgnoreCase))
            {
                verifyArg = "--verify";
                break;
            }
        }

        Console.WriteLine($"[ntKDE] Spawning KDE foreign window presenter over in-kernel stdio pipe (Zero-TCP)...");
        var wslArgs = $"-d Ubuntu -- bash -c \"PYTHONUNBUFFERED=1 DISPLAY=:0 python3 -u \\\"{presenterPath}\\\" --stdio \\\"{targetDisplayName} (ntKDE)\\\" {verifyArg}\"".Trim();

        var psi = new ProcessStartInfo("wsl.exe", wslArgs)
        {
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = false,
        };

        using var wslProc = Process.Start(psi);
        if (wslProc == null)
        {
            Console.WriteLine("[ntKDE] Error: failed to launch WSL presenter process.");
            return;
        }

        // Start bidirectional pipe streaming over stdio
        streamer.StartPipedSession(wslProc.StandardOutput.BaseStream, wslProc.StandardInput.BaseStream);

        Console.WriteLine($"[ntKDE] Path B Active! Windows application is composed inside KDE over Zero-TCP pipe stream.");
        wslProc.WaitForExit();
    }

    public static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current != null)
        {
            if (File.Exists(Path.Combine(current.FullName, "README.md")) &&
                Directory.Exists(Path.Combine(current.FullName, "wsl")))
            {
                return current.FullName;
            }
            current = current.Parent;
        }
        return AppContext.BaseDirectory;
    }

    public static string ConvertToWslPath(string windowsPath)
    {
        var full = Path.GetFullPath(windowsPath);
        if (full.Length >= 2 && full[1] == ':')
        {
            return $"/mnt/{char.ToLowerInvariant(full[0])}{full[2..].Replace('\\', '/')}";
        }
        return windowsPath.Replace('\\', '/');
    }

    public static void HandleListWindows()
    {
        Console.WriteLine("[ntKDE] Enumerating visible windows...");
        var container = ContainerWindowManager.FindContainerWindow();
        Console.WriteLine($"[ntKDE] ContainerWindowManager.FindContainerWindow() => 0x{container:X}");
        if (container != nint.Zero)
        {
            var sbTitle = new StringBuilder(512);
            NativeWindowDiscovery.GetWindowText(container, sbTitle, 512);
            var sbClass = new StringBuilder(512);
            NativeWindowDiscovery.GetClassName(container, sbClass, 512);
            Console.WriteLine($"[ntKDE]   Class: '{sbClass}' | Title: '{sbTitle}'");
        }

        var discovery = NativeWindowDiscovery.Find("msrdc");
        Console.WriteLine($"[ntKDE] NativeWindowDiscovery.Find('msrdc') => {discovery.Status} ({discovery.Windows.Count} windows)");
        foreach (var w in discovery.Windows)
        {
            var sbTitle = new StringBuilder(512);
            NativeWindowDiscovery.GetWindowText(w, sbTitle, 512);
            var sbClass = new StringBuilder(512);
            NativeWindowDiscovery.GetClassName(w, sbClass, 512);
            NativeWindowDiscovery.GetClientRect(w, out var cr);
            NativeWindowDiscovery.GetWindowRect(w, out var wr);
            var vis = NativeWindowDiscovery.IsWindowVisible(w);
            var style = NativeWindowDiscovery.GetWindowLongPtr(w, -16);
            Console.WriteLine($"[ntKDE]   HWND: 0x{w:X} | Vis: {vis} | Pos: ({wr.Left},{wr.Top}) to ({wr.Right},{wr.Bottom}) [{wr.Right - wr.Left}x{wr.Bottom - wr.Top}] | Client: {cr.Right - cr.Left}x{cr.Bottom - cr.Top} | Class: '{sbClass}' | Title: '{sbTitle}' | Style: 0x{style:X}");
        }
    }
}

internal sealed class NtKdeTrayContext : ApplicationContext
{
    private readonly NotifyIcon trayIcon;
    private readonly GlobalHotkeyManager hotkeyManager;
    private readonly AudioVolumeBridge audioBridge;
    private readonly NotificationBridge notificationBridge;
    private readonly System.Windows.Forms.Timer windowHookTimer;
    private readonly WindowsAppSyncRunner appSyncRunner;
    private readonly WindowsTaskTracker taskTracker;
    private readonly Rectangle targetBounds;
    private readonly bool borderless;
    private readonly bool hideExplorer;
    private readonly MultiMonitorDesktopManager? desktopMgr;
    private nint hookedContainerHwnd = nint.Zero;

    public NtKdeTrayContext(Rectangle targetBounds, bool borderless, bool hideExplorer, MultiMonitorDesktopManager? desktopMgr = null)
    {
        this.targetBounds = targetBounds;
        this.borderless = borderless;
        this.hideExplorer = hideExplorer;
        this.desktopMgr = desktopMgr;

        // Start background app sync runner (watches Start Menu for setup.exe / installations)
        appSyncRunner = new WindowsAppSyncRunner();

        // Start Windows Task Tracker (mirrors Windows applications into KDE Plasma taskbar)
        taskTracker = new WindowsTaskTracker();
        taskTracker.BridgeStatusChanged += OnBridgeStatusChanged;
        taskTracker.Start();

        // Initialize Notification and Audio Bridges
        notificationBridge = new NotificationBridge(taskTracker);
        audioBridge = new AudioVolumeBridge();
        audioBridge.VolumeChanged += (vol, muted) =>
        {
            var pct = (int)Math.Round(vol * 100);
            taskTracker.SendVolume(pct);
        };
        audioBridge.StartMonitoring();

        // 1. Build System Tray Icon
        trayIcon = new NotifyIcon
        {
            Icon = CreateNtKdeIcon(),
            Text = "ntKDE - Hybrid KDE Plasma Desktop",
            Visible = true,
            ContextMenuStrip = CreateContextMenu(),
        };

        trayIcon.DoubleClick += (_, _) => FocusKdeDesktop();

        // 2. Global Hotkey Handler
        hotkeyManager = new GlobalHotkeyManager();
        hotkeyManager.EmergencyRecovery += OnEmergencyRecovery;
        hotkeyManager.KickoffRequested += () => taskTracker.TriggerKickoff();
        hotkeyManager.KRunnerRequested += () => taskTracker.TriggerKRunner();
        hotkeyManager.KonsoleRequested += () => Program.HandleApp(new[] { "app", "konsole" });
        hotkeyManager.DolphinRequested += () => Program.HandleApp(new[] { "app", "dolphin" });

        // 3. Container Window Framing Hook
        windowHookTimer = new System.Windows.Forms.Timer { Interval = 600 };
        windowHookTimer.Tick += OnHookTimerTick;
        windowHookTimer.Start();

        trayIcon.ShowBalloonTip(
            3000,
            "ntKDE Active",
            "KDE Plasma desktop session is running.\nHotkeys: Super (Kickoff), Alt+Space (KRunner), Win+T (Konsole), Win+E (Dolphin)",
            ToolTipIcon.Info);

        DiagnosticLog.Info("Tray", "NtKdeTrayContext initialized.");
    }

    private void OnBridgeStatusChanged(WindowsTaskTracker.BridgeState newState)
    {
        var statusText = newState switch
        {
            WindowsTaskTracker.BridgeState.Running => "Full",
            WindowsTaskTracker.BridgeState.Restarting => "Reconnecting...",
            WindowsTaskTracker.BridgeState.Dead => "Degraded (bridge down)",
            _ => "Starting"
        };
        trayIcon.Text = $"ntKDE - {statusText}";

        if (newState == WindowsTaskTracker.BridgeState.Dead)
        {
            trayIcon.ShowBalloonTip(5000, "ntKDE Warning",
                "KDE task bridge is unavailable. Taskbar integration is degraded.\nWindows apps remain functional.",
                ToolTipIcon.Warning);
        }
    }

    private ContextMenuStrip CreateContextMenu()
    {
        var menu = new ContextMenuStrip();

        var header = new ToolStripMenuItem("⚡ ntKDE Hybrid Desktop") { Enabled = false };
        header.Font = new Font(header.Font, FontStyle.Bold);
        menu.Items.Add(header);
        menu.Items.Add(new ToolStripSeparator());

        menu.Items.Add("▶ Start / Resume KDE Plasma", null, (_, _) =>
            Program.StartDesktopSession(targetBounds.Width, targetBounds.Height));
        menu.Items.Add("⏹ Stop KDE Session", null, (_, _) =>
            Program.HandleStop());
        menu.Items.Add(new ToolStripSeparator());

        menu.Items.Add("🗂 Open Dolphin File Manager (Win+E)", null, (_, _) =>
            Program.HandleApp(new[] { "app", "dolphin" }));
        menu.Items.Add("💻 Open Konsole Terminal (Win+T)", null, (_, _) =>
            Program.HandleApp(new[] { "app", "konsole" }));
        menu.Items.Add("🔍 Open KRunner (Alt+Space)", null, (_, _) =>
            Program.HandleApp(new[] { "app", "krunner" }));
        menu.Items.Add("⚙ Open KDE System Settings", null, (_, _) =>
            Program.HandleApp(new[] { "app", "systemsettings" }));
        menu.Items.Add(new ToolStripSeparator());

        menu.Items.Add("🔄 Sync Windows Apps & Icons to KDE", null, (_, _) =>
            Task.Run(() => Program.HandleSync()));

        var shellSubMenu = new ToolStripMenuItem("🛡 Windows Shell Options");
        shellSubMenu.DropDownItems.Add("Set ntKDE as Winlogon Shell", null, (_, _) =>
        {
            var exePath = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName;
            if (!string.IsNullOrEmpty(exePath))
            {
                ShellRegistry.SetShell(exePath);
                MessageBox.Show($"ntKDE configured as Windows Shell:\n{exePath}", "ntKDE Shell", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
        });
        shellSubMenu.DropDownItems.Add("Restore Explorer Shell (Default)", null, (_, _) =>
        {
            ShellRegistry.RestoreShell();
            MessageBox.Show("Windows Shell restored to default (explorer.exe).", "ntKDE Shell", MessageBoxButtons.OK, MessageBoxIcon.Information);
        });
        menu.Items.Add(shellSubMenu);

        menu.Items.Add(new ToolStripSeparator());

        // Diagnostics menu item
        menu.Items.Add("📋 Open Diagnostics Logs", null, (_, _) =>
        {
            try
            {
                Process.Start(new ProcessStartInfo(DiagnosticLog.LogDir) { UseShellExecute = true });
            }
            catch { }
        });

        menu.Items.Add("❌ Exit ntKDE", null, (_, _) => ExitSession());

        return menu;
    }

    private void OnHookTimerTick(object? sender, EventArgs e)
    {
        // When native Plasma desktop surfaces are active, hide the fallback WinForms surfaces
        desktopMgr?.SetSurfacesVisible(!KdePanelManager.HasNativeDesktops);

        var hwnd = ContainerWindowManager.FindContainerWindow();
        if (hwnd != nint.Zero && hwnd != hookedContainerHwnd)
        {
            hookedContainerHwnd = hwnd;
            if (borderless)
            {
                ContainerWindowManager.MakeBorderless(hookedContainerHwnd, targetBounds);
            }
            ContainerWindowManager.Activate(hookedContainerHwnd);
        }
    }

    private void FocusKdeDesktop()
    {
        if (hookedContainerHwnd != nint.Zero)
        {
            ContainerWindowManager.Activate(hookedContainerHwnd);
        }
        else
        {
            var hwnd = ContainerWindowManager.FindContainerWindow();
            if (hwnd != nint.Zero)
            {
                hookedContainerHwnd = hwnd;
                ContainerWindowManager.Activate(hookedContainerHwnd);
            }
            else
            {
                // In native mode, focus the primary monitor's KDE Desktop surface
                KdePanelManager.FocusPrimaryDesktop();
            }
        }
    }

    private void OnEmergencyRecovery()
    {
        try
        {
            Process.Start(new ProcessStartInfo("explorer.exe") { UseShellExecute = true });
        }
        catch
        {
        }
        ExitSession();
    }

    private void ExitSession()
    {
        DiagnosticLog.Info("Tray", "ExitSession initiated.");
        windowHookTimer.Stop();
        windowHookTimer.Dispose();
        taskTracker.BridgeStatusChanged -= OnBridgeStatusChanged;
        taskTracker.Dispose();
        appSyncRunner.Dispose();
        hotkeyManager.Dispose();
        audioBridge.Dispose();
        notificationBridge.Dispose();
        trayIcon.Visible = false;
        trayIcon.Dispose();

        if (hideExplorer)
        {
            ExplorerHider.SetVisibility(true);
        }

        Program.HandleStop();
        DiagnosticLog.Info("Tray", "Session exited cleanly.");
        Application.Exit();
    }

    private static Icon CreateNtKdeIcon()
    {
        using var bitmap = new Bitmap(32, 32);
        using var g = Graphics.FromImage(bitmap);
        g.SmoothingMode = SmoothingMode.AntiAlias;

        // Breeze Dark circular background
        using var brush = new SolidBrush(Color.FromArgb(35, 38, 41));
        g.FillEllipse(brush, 1, 1, 30, 30);

        // Cyan accent ring
        using var ringPen = new Pen(Color.FromArgb(61, 174, 233), 2.2f);
        g.DrawEllipse(ringPen, 1, 1, 30, 30);

        // Stylized "K" emblem
        using var kPen = new Pen(Color.White, 2.8f) { StartCap = LineCap.Round, EndCap = LineCap.Round };
        g.DrawLine(kPen, 11, 8, 11, 24);
        g.DrawLine(kPen, 21, 9, 11, 16);
        g.DrawLine(kPen, 11, 16, 21, 23);

        return Icon.FromHandle(bitmap.GetHicon());
    }
}

internal static class ContainerWindowManager
{
    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, nint lParam);
    private delegate bool EnumWindowsProc(nint hWnd, nint lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(nint hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(nint hWnd);

    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")]
    private static extern nint GetWindowLongPtr(nint hWnd, int nIndex);

    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")]
    private static extern nint SetWindowLongPtr(nint hWnd, int nIndex, nint dwNewLong);

    [DllImport("user32.dll")]
    private static extern bool SetWindowPos(nint hWnd, nint hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(nint hWnd);

    private const int GWL_STYLE = -16;
    private const long WS_CAPTION = 0x00C00000L;
    private const long WS_THICKFRAME = 0x00040000L;
    private const long WS_MINIMIZEBOX = 0x00020000L;
    private const long WS_MAXIMIZEBOX = 0x00010000L;
    private const long WS_SYSMENU = 0x00080000L;

    private const uint SWP_FRAMECHANGED = 0x0020;
    private const uint SWP_SHOWWINDOW = 0x0040;

    [DllImport("user32.dll")]
    private static extern bool EnumDesktopWindows(nint hDesktop, EnumWindowsProc lpfn, nint lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern nint OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll")]
    private static extern bool CloseDesktop(nint hDesktop);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(nint hWnd, StringBuilder lpClassName, int nMaxCount);

    public static nint FindContainerWindow()
    {
        nint found = nint.Zero;
        var currentPid = (uint)Environment.ProcessId;
        bool Callback(nint hWnd, nint _)
        {
            if (!IsWindowVisible(hWnd)) return true;
            GetWindowThreadProcessId(hWnd, out var pid);
            if (pid == currentPid) return true;

            var sbClass = new StringBuilder(256);
            GetClassName(hWnd, sbClass, 256);
            var className = sbClass.ToString();
            if (!className.Equals("RAIL_WINDOW", StringComparison.OrdinalIgnoreCase)) return true;

            var sb = new StringBuilder(512);
            if (GetWindowText(hWnd, sb, 512) > 0)
            {
                var title = sb.ToString();
                // CRITICAL: Ignore native Plasma windows (Desktop @ QRect and plasmashell panel)
                // These are managed natively by KdePanelManager.
                if (title.Contains("Desktop @", StringComparison.OrdinalIgnoreCase) ||
                    title.Contains("plasmashell", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }

                // Only match standalone nested compositors (Weston, Xephyr, nested KWin container)
                if (title.Contains("KDE Wayland Compositor", StringComparison.OrdinalIgnoreCase) ||
                    title.Contains("ntKDE - KDE Plasma Desktop", StringComparison.OrdinalIgnoreCase) ||
                    title.Contains("Authentic Linux Desktop - Plasma", StringComparison.OrdinalIgnoreCase) ||
                    title.Contains("Weston", StringComparison.OrdinalIgnoreCase) ||
                    title.Contains("Xephyr", StringComparison.OrdinalIgnoreCase))
                {
                    found = hWnd;
                    return false;
                }
            }
            return true;
        }

        var hDesk = OpenDesktop("default", 0, false, 0x01FF);
        if (hDesk != nint.Zero)
        {
            try
            {
                EnumDesktopWindows(hDesk, Callback, nint.Zero);
            }
            finally
            {
                CloseDesktop(hDesk);
            }
        }

        if (found == nint.Zero)
        {
            EnumWindows(Callback, nint.Zero);
        }

        return found;
    }

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(nint hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    private static extern bool BringWindowToTop(nint hWnd);

    public static void MakeBorderless(nint hWnd, Rectangle bounds)
    {
        if (hWnd == nint.Zero) return;
        ShowWindow(hWnd, 9); // SW_RESTORE
        var style = GetWindowLongPtr(hWnd, GWL_STYLE).ToInt64();
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU);
        SetWindowLongPtr(hWnd, GWL_STYLE, (nint)style);
        SetWindowPos(hWnd, new nint(-1) /* HWND_TOPMOST */, bounds.X, bounds.Y, bounds.Width, bounds.Height,
            SWP_FRAMECHANGED | SWP_SHOWWINDOW);
        SetWindowPos(hWnd, new nint(-2) /* HWND_NOTOPMOST */, bounds.X, bounds.Y, bounds.Width, bounds.Height,
            SWP_FRAMECHANGED | SWP_SHOWWINDOW);
        ShowWindow(hWnd, 5); // SW_SHOW
        BringWindowToTop(hWnd);
        SetForegroundWindow(hWnd);
    }

    public static void Activate(nint hWnd)
    {
        if (hWnd != nint.Zero)
        {
            ShowWindow(hWnd, 9); // SW_RESTORE
            ShowWindow(hWnd, 5); // SW_SHOW
            BringWindowToTop(hWnd);
            SetForegroundWindow(hWnd);
        }
    }
}

internal static class WslSessionProbe
{
    public static string GetStatus()
    {
        using var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = "wsl.exe",
                Arguments = "-d Ubuntu -- bash -lc \"printf WSL_READY\"",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            },
        };

        try
        {
            process.Start();
            var output = process.StandardOutput.ReadToEnd().Trim();
            process.WaitForExit(5000);
            return process.ExitCode == 0 && output == "WSL_READY"
                ? "WSL Ubuntu: connected"
                : "WSL Ubuntu: unavailable";
        }
        catch (Exception)
        {
            return "WSL Ubuntu: unavailable";
        }
    }
}

internal static class NativeWindowDiscovery
{
    public sealed record DiscoveryResult(IReadOnlyList<nint> Windows, string Status);

    [StructLayout(LayoutKind.Sequential)]
    internal struct Rect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    private delegate bool EnumWindowsCallback(nint window, nint parameter);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsCallback callback, nint parameter);

    [DllImport("user32.dll")]
    private static extern bool EnumDesktopWindows(nint hDesktop, EnumWindowsCallback lpfn, nint lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern nint OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll")]
    private static extern bool CloseDesktop(nint hDesktop);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint window, out uint processId);

    [DllImport("user32.dll")]
    internal static extern bool IsWindowVisible(nint window);

    [DllImport("user32.dll")]
    internal static extern bool GetClientRect(nint window, out Rect clientRect);

    [DllImport("user32.dll")]
    internal static extern bool GetWindowRect(nint window, out Rect windowRect);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    internal static extern int GetWindowText(nint window, StringBuilder text, int length);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    internal static extern int GetClassName(nint window, StringBuilder text, int length);

    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")]
    internal static extern nint GetWindowLongPtr(nint hWnd, int nIndex);

    public static DiscoveryResult Find(string? processName)
    {
        if (string.IsNullOrWhiteSpace(processName))
        {
            return new DiscoveryResult(Array.Empty<nint>(), "native capture: disabled");
        }

        var normalizedName = Path.GetFileNameWithoutExtension(processName);
        var matches = new List<nint>();

        bool ProcessWindow(nint window, nint _)
        {
            if (!IsWindowVisible(window)) return true;
            GetWindowThreadProcessId(window, out var pid);
            try
            {
                var process = Process.GetProcessById((int)pid);
                var isProcMatch = string.Equals(process.ProcessName, normalizedName, StringComparison.OrdinalIgnoreCase);

                var sb = new StringBuilder(512);
                var length = GetWindowText(window, sb, sb.Capacity);
                var title = length > 0 ? sb.ToString() : string.Empty;

                var isTitleMatch = !string.IsNullOrEmpty(title) &&
                                   title.Contains(normalizedName, StringComparison.OrdinalIgnoreCase);

                if (isProcMatch || isTitleMatch)
                {
                    GetClientRect(window, out var rect);
                    var width = rect.Right - rect.Left;
                    var height = rect.Bottom - rect.Top;
                    if (width > 20 && height > 20 && !matches.Contains(window))
                    {
                        matches.Add(window);
                    }
                }
            }
            catch { }
            return true;
        }

        var hDefaultDesk = OpenDesktop("default", 0, false, 0x01FF);
        if (hDefaultDesk != nint.Zero)
        {
            try
            {
                EnumDesktopWindows(hDefaultDesk, ProcessWindow, nint.Zero);
            }
            finally
            {
                CloseDesktop(hDefaultDesk);
            }
        }

        if (matches.Count == 0)
        {
            EnumWindows(ProcessWindow, nint.Zero);
        }

        return matches.Count == 0
            ? new DiscoveryResult(Array.Empty<nint>(), $"no visible window found for {normalizedName}")
            : new DiscoveryResult(matches, $"tracking {matches.Count} window(s) for {normalizedName}");
    }
}