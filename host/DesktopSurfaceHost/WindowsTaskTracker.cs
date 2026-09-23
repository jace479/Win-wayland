using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace NtPlasma.DesktopSurfaceHost;

/// <summary>
/// Tracks active top-level Windows application windows using Win32 WinEvent hooks,
/// projects them into the KDE Plasma Task Manager via kde-task-bridge.py in WSL,
/// and routes interactive taskbar actions (activate, minimize, close) back to the native HWNDs.
/// Strictly Zero-TCP: uses standard piped in-kernel stdio.
/// Includes watchdog auto-restart with exponential backoff on bridge process crash.
/// </summary>
internal sealed class WindowsTaskTracker : IDisposable
{
    private const uint EventMin = 0x0001;
    private const uint EventMax = 0x800C;
    private const uint EventObjectShow = 0x8002;
    private const uint EventObjectHide = 0x8003;
    private const uint EventObjectLocationChange = 0x800B;
    private const uint EventSystemForeground = 0x0003;
    private const uint EventObjectNameChange = 0x800C;
    private const uint WinEventOutOfContext = 0;
    private const uint WinEventSkipOwnProcess = 2;

    private const int GWL_STYLE = -16;
    private const int GWL_EXSTYLE = -20;
    private const uint WS_CHILD = 0x40000000;
    private const uint WS_VISIBLE = 0x10000000;
    private const uint WS_EX_TOOLWINDOW = 0x00000080;
    private const uint WS_EX_APPWINDOW = 0x00040000;
    private const uint GA_ROOTOWNER = 3;

    private const int SW_HIDE = 0;
    private const int SW_NORMAL = 1;
    private const int SW_SHOW = 5;
    private const int SW_MINIMIZE = 6;
    private const int SW_RESTORE = 9;
    private const uint WM_CLOSE = 0x0010;
    private const uint MONITOR_DEFAULTTONEAREST = 2;

    // Watchdog constants
    private const int MaxBridgeRestarts = 5;
    private static readonly int[] BackoffMs = { 1000, 2000, 4000, 8000, 16000 };
    private const string LogComponent = "TaskTracker";

    private readonly ConcurrentDictionary<nint, TrackedTask> _trackedTasks = new();
    private readonly WinEventDelegate _winEventCallback;
    private readonly System.Threading.Timer _periodicSyncTimer;
    private nint _hook;
    private Process? _bridgeProcess;
    private StreamWriter? _bridgeInput;
    private CancellationTokenSource _cts = new();
    private bool _disposed;

    // Watchdog state
    private int _bridgeRestartCount;
    private int _isRestarting;
    private volatile bool _bridgeDead;
    private readonly object _bridgeLock = new();
    private volatile nint _lastActiveAppHwnd = nint.Zero;
    private volatile bool _anyFullscreen;

    public enum BridgeState { Running, Restarting, Dead, NotStarted }

    /// <summary>Current health status of the bridge process.</summary>
    public BridgeState BridgeStatus { get; private set; } = BridgeState.NotStarted;

    /// <summary>Raised when bridge status changes.</summary>
    public event Action<BridgeState>? BridgeStatusChanged;

    public WindowsTaskTracker()
    {
        _winEventCallback = OnWinEvent;
        _periodicSyncTimer = new System.Threading.Timer(_ => PerformSync(), null, Timeout.Infinite, Timeout.Infinite);
    }

    public void Start()
    {
        if (_disposed) return;

        try
        {
            StartBridgeProcess();
            InstallHook();
            PerformSync();

            // Periodic reconciliation every 4 seconds
            _periodicSyncTimer.Change(TimeSpan.FromSeconds(4), TimeSpan.FromSeconds(4));
            DiagnosticLog.Info(LogComponent, "WindowsTaskTracker started successfully.");
        }
        catch (Exception ex)
        {
            DiagnosticLog.Error(LogComponent, "WindowsTaskTracker start error", ex);
        }
    }

    private void StartBridgeProcess()
    {
        lock (_bridgeLock)
        {
            // Clean up any previous process
            if (_bridgeProcess != null)
            {
                try
                {
                    _bridgeProcess.Exited -= OnBridgeProcessExited;
                    _bridgeInput?.Close();
                    if (!_bridgeProcess.HasExited) _bridgeProcess.Kill();
                }
                catch { }
                _bridgeProcess.Dispose();
                _bridgeProcess = null;
                _bridgeInput = null;
            }

            _bridgeDead = false;

            var repoRoot = Program.FindRepoRoot();
            var scriptPath = Path.Combine(repoRoot, "wsl", "kde-task-bridge.py");
            var wslScriptPath = Program.ConvertToWslPath(scriptPath);

            var psi = new ProcessStartInfo("wsl.exe", $"-d Ubuntu -u jace479 -e python3 -u \"{wslScriptPath}\"")
            {
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            };

            _bridgeProcess = Process.Start(psi);
            if (_bridgeProcess == null)
            {
                DiagnosticLog.Warn(LogComponent, "Failed to spawn kde-task-bridge.py in WSL.");
                SetBridgeStatus(BridgeState.Dead);
                return;
            }

            _bridgeInput = _bridgeProcess.StandardInput;

            // Watch for unexpected exits
            _bridgeProcess.EnableRaisingEvents = true;
            _bridgeProcess.Exited += OnBridgeProcessExited;

            SetBridgeStatus(BridgeState.Running);
            DiagnosticLog.Info(LogComponent, $"Bridge process started (PID {_bridgeProcess.Id}, restart #{_bridgeRestartCount}).");

            // Background reader for inbound commands from KDE
            Task.Run(ReadBridgeOutputAsync, _cts.Token);
            Task.Run(ReadBridgeErrorAsync, _cts.Token);
        }
    }

    private void OnBridgeProcessExited(object? sender, EventArgs e)
    {
        if (_disposed || _cts.IsCancellationRequested) return;

        var exitCode = -1;
        try { exitCode = _bridgeProcess?.ExitCode ?? -1; } catch { }

        DiagnosticLog.Warn(LogComponent, $"Bridge process exited unexpectedly (exit code {exitCode}).");
        ScheduleBridgeRestart();
    }

    private void ScheduleBridgeRestart()
    {
        if (_disposed || _cts.IsCancellationRequested) return;

        // Atomic check to prevent concurrent callers (hooks + timer + exit event) from burning all restart attempts
        if (Interlocked.CompareExchange(ref _isRestarting, 1, 0) != 0)
        {
            return;
        }

        if (_bridgeRestartCount >= MaxBridgeRestarts)
        {
            DiagnosticLog.Error(LogComponent, $"Bridge process exceeded max restarts ({MaxBridgeRestarts}). Giving up.");
            SetBridgeStatus(BridgeState.Dead);
            _bridgeDead = true;
            _isRestarting = 0;
            return;
        }

        var backoffIndex = Math.Min(_bridgeRestartCount, BackoffMs.Length - 1);
        var delayMs = BackoffMs[backoffIndex];
        _bridgeRestartCount++;

        SetBridgeStatus(BridgeState.Restarting);
        DiagnosticLog.Info(LogComponent, $"Scheduling bridge restart #{_bridgeRestartCount} in {delayMs}ms...");

        Task.Delay(delayMs, _cts.Token).ContinueWith(_ =>
        {
            try
            {
                if (_disposed || _cts.IsCancellationRequested) return;

                StartBridgeProcess();

                // Re-sync all tracked tasks to the new bridge instance
                if (!_bridgeDead)
                {
                    DiagnosticLog.Info(LogComponent, "Re-syncing all tracked tasks to restarted bridge.");
                    PerformSync();
                }
            }
            catch (Exception ex)
            {
                DiagnosticLog.Error(LogComponent, "Bridge restart failed", ex);
                _isRestarting = 0;
                ScheduleBridgeRestart();
                return;
            }
            finally
            {
                _isRestarting = 0;
            }
        }, TaskScheduler.Default);
    }

    private void SetBridgeStatus(BridgeState newStatus)
    {
        if (BridgeStatus == newStatus) return;
        var oldStatus = BridgeStatus;
        BridgeStatus = newStatus;
        DiagnosticLog.Transition(LogComponent, oldStatus.ToString(), newStatus.ToString(), "bridge lifecycle");
        try { BridgeStatusChanged?.Invoke(newStatus); } catch { }
    }

    private async Task ReadBridgeOutputAsync()
    {
        if (_bridgeProcess == null) return;
        var reader = _bridgeProcess.StandardOutput;

        try
        {
            while (!_cts.Token.IsCancellationRequested && !reader.EndOfStream)
            {
                var line = await reader.ReadLineAsync();
                if (string.IsNullOrWhiteSpace(line)) continue;

                HandleBridgeCommand(line);
            }
        }
        catch (Exception)
        {
            // stream closed or cancelled
        }
    }

    private async Task ReadBridgeErrorAsync()
    {
        if (_bridgeProcess == null) return;
        var reader = _bridgeProcess.StandardError;
        try
        {
            while (!_cts.Token.IsCancellationRequested && !reader.EndOfStream)
            {
                var line = await reader.ReadLineAsync();
                if (!string.IsNullOrWhiteSpace(line))
                {
                    DiagnosticLog.Info("task-bridge", line);
                }
            }
        }
        catch { }
    }

    private void HandleBridgeCommand(string jsonLine)
    {
        try
        {
            using var doc = JsonDocument.Parse(jsonLine);
            var root = doc.RootElement;
            var op = root.TryGetProperty("op", out var opProp) ? opProp.GetString() :
                     root.TryGetProperty("action", out var actProp) ? actProp.GetString() : null;
            if (string.IsNullOrEmpty(op)) return;

            if (op is "show_desktop" or "minimize_all" or "restore_all" or "toggle_desktop")
            {
                if (op == "minimize_all")
                {
                    MinimizeAll();
                }
                else if (op == "restore_all")
                {
                    RestoreAll();
                }
                else
                {
                    ToggleDesktop();
                }
                return;
            }

            var hwndVal = root.TryGetProperty("hwnd", out var hProp) && hProp.ValueKind == JsonValueKind.Number ? hProp.GetInt64() : 0;
            var hwnd = (nint)hwndVal;
            if (hwnd == nint.Zero || !IsWindow(hwnd)) return;

            switch (op)
            {
                case "activate":
                    ActivateWindow(hwnd);
                    break;

                case "minimize":
                    ShowWindow(hwnd, SW_MINIMIZE);
                    if (_lastActiveAppHwnd == hwnd) _lastActiveAppHwnd = nint.Zero;
                    break;

                case "restore":
                    ActivateWindow(hwnd);
                    break;

                case "toggle":
                    if ((_lastActiveAppHwnd == hwnd || GetForegroundWindow() == hwnd) && !IsIconic(hwnd))
                    {
                        ShowWindow(hwnd, SW_MINIMIZE);
                        _lastActiveAppHwnd = nint.Zero;
                    }
                    else
                    {
                        ActivateWindow(hwnd);
                    }
                    break;

                case "close":
                    PostMessage(hwnd, WM_CLOSE, nint.Zero, nint.Zero);
                    break;
            }
        }
        catch (Exception ex)
        {
            DiagnosticLog.Error(LogComponent, "Failed to handle task bridge command", ex);
        }
    }

    private void ActivateWindow(nint hwnd)
    {
        try
        {
            if (IsIconic(hwnd))
            {
                ShowWindow(hwnd, SW_RESTORE);
            }

            var fgHwnd = GetForegroundWindow();
            var fgThread = GetWindowThreadProcessId(fgHwnd, out _);
            var curThread = GetCurrentThreadId();

            if (fgThread != 0 && fgThread != curThread)
            {
                AttachThreadInput(curThread, fgThread, true);
            }

            BringWindowToTop(hwnd);
            ShowWindow(hwnd, SW_SHOW);
            SetForegroundWindow(hwnd);
            SwitchToThisWindow(hwnd, true);

            if (fgThread != 0 && fgThread != curThread)
            {
                AttachThreadInput(curThread, fgThread, false);
            }

            _lastActiveAppHwnd = hwnd;
        }
        catch (Exception ex)
        {
            DiagnosticLog.Warn(LogComponent, $"ActivateWindow failed: {ex.Message}");
        }
    }

    private static void ToggleDesktop()
    {
        try
        {
            var shellType = Type.GetTypeFromProgID("Shell.Application");
            if (shellType != null)
            {
                dynamic? shell = Activator.CreateInstance(shellType);
                shell?.ToggleDesktop();
            }
        }
        catch (Exception ex)
        {
            DiagnosticLog.Warn(LogComponent, $"ToggleDesktop failed: {ex.Message}");
        }
    }

    private static void MinimizeAll()
    {
        try
        {
            var shellType = Type.GetTypeFromProgID("Shell.Application");
            if (shellType != null)
            {
                dynamic? shell = Activator.CreateInstance(shellType);
                shell?.MinimizeAll();
            }
        }
        catch (Exception ex)
        {
            DiagnosticLog.Warn(LogComponent, $"MinimizeAll failed: {ex.Message}");
        }
    }

    private static void RestoreAll()
    {
        try
        {
            var shellType = Type.GetTypeFromProgID("Shell.Application");
            if (shellType != null)
            {
                dynamic? shell = Activator.CreateInstance(shellType);
                shell?.UndoMinimizeALL();
            }
        }
        catch (Exception ex)
        {
            DiagnosticLog.Warn(LogComponent, $"RestoreAll failed: {ex.Message}");
        }
    }

    private void InstallHook()
    {
        _hook = SetWinEventHook(
            EventMin,
            EventMax,
            nint.Zero,
            _winEventCallback,
            0,
            0,
            WinEventOutOfContext | WinEventSkipOwnProcess);
    }

    private void OnWinEvent(
        nint hook,
        uint eventType,
        nint hwnd,
        int objectId,
        int childId,
        uint threadId,
        uint eventTime)
    {
        if (hwnd == nint.Zero || objectId != 0 || childId != 0) return;

        if (eventType == EventSystemForeground)
        {
            if (_trackedTasks.ContainsKey(hwnd))
            {
                _lastActiveAppHwnd = hwnd;
                SendToBridge(new { op = "active", hwnd = (long)hwnd });
            }
            else if (IsQualifyingAppWindow(hwnd, out var title, out var processName, out var appId, out var pid))
            {
                var isMinimized = IsIconic(hwnd);
                _trackedTasks[hwnd] = new TrackedTask(hwnd, title, appId, processName, pid, isMinimized, true);
                _lastActiveAppHwnd = hwnd;
                SendToBridge(new
                {
                    op = "add",
                    hwnd = (long)hwnd,
                    title = title,
                    appId = appId,
                    process = processName,
                    pid = pid,
                    minimized = isMinimized,
                    active = true
                });
            }
            CheckAndSendFullscreenState();
            return;
        }

        if (eventType is EventObjectShow or EventObjectNameChange or EventObjectLocationChange)
        {
            if (IsQualifyingAppWindow(hwnd, out var title, out var processName, out var appId, out var pid))
            {
                var isMinimized = IsIconic(hwnd);
                var isActive = GetForegroundWindow() == hwnd;

                if (_trackedTasks.TryGetValue(hwnd, out var existing))
                {
                    if (existing.Title != title || existing.IsMinimized != isMinimized)
                    {
                        _trackedTasks[hwnd] = new TrackedTask(hwnd, title, appId, processName, pid, isMinimized, isActive);
                        SendToBridge(new { op = "update", hwnd = (long)hwnd, title = title, minimized = isMinimized });
                    }
                }
                else
                {
                    _trackedTasks[hwnd] = new TrackedTask(hwnd, title, appId, processName, pid, isMinimized, isActive);
                    SendToBridge(new
                    {
                        op = "add",
                        hwnd = (long)hwnd,
                        title = title,
                        appId = appId,
                        process = processName,
                        pid = pid,
                        minimized = isMinimized,
                        active = isActive
                    });
                }
            }
            else
            {
                // Not qualifying anymore (e.g. hidden or closed)
                if (_trackedTasks.TryRemove(hwnd, out _))
                {
                    SendToBridge(new { op = "remove", hwnd = (long)hwnd });
                }
            }
        }
        else if (eventType is EventObjectHide)
        {
            if (!IsWindowVisible(hwnd) && _trackedTasks.TryRemove(hwnd, out _))
            {
                SendToBridge(new { op = "remove", hwnd = (long)hwnd });
            }
        }
    }

    public void PerformSync()
    {
        try
        {
            var activeHwnds = new HashSet<nint>();
            var tasksList = new List<object>();

            bool ProcessHwnd(nint hwnd)
            {
                if (IsQualifyingAppWindow(hwnd, out var title, out var processName, out var appId, out var pid))
                {
                    activeHwnds.Add(hwnd);
                    var isMinimized = IsIconic(hwnd);
                    var isActive = GetForegroundWindow() == hwnd;
                    _trackedTasks[hwnd] = new TrackedTask(hwnd, title, appId, processName, pid, isMinimized, isActive);

                    tasksList.Add(new
                    {
                        hwnd = (long)hwnd,
                        title = title,
                        appId = appId,
                        process = processName,
                        pid = pid,
                        minimized = isMinimized,
                        active = isActive
                    });
                }
                return true;
            }

            nint hDesk = OpenDesktop("default", 0, false, 0x01FF);
            if (hDesk != nint.Zero)
            {
                try
                {
                    EnumDesktopWindows(hDesk, (hwnd, _) => ProcessHwnd(hwnd), nint.Zero);
                }
                finally
                {
                    CloseDesktop(hDesk);
                }
            }
            else
            {
                EnumWindows((hwnd, _) => ProcessHwnd(hwnd), nint.Zero);
            }

            // Remove dead tasks
            foreach (var hwnd in _trackedTasks.Keys)
            {
                if (!activeHwnds.Contains(hwnd))
                {
                    _trackedTasks.TryRemove(hwnd, out _);
                }
            }

            SendToBridge(new { op = "sync", tasks = tasksList });
            CheckAndSendFullscreenState();
        }
        catch (Exception ex)
        {
            DiagnosticLog.Error(LogComponent, "Error during PerformSync", ex);
        }
    }

    public void SendNotification(string title, string body, string appName = "Windows", string urgency = "normal", string icon = "preferences-desktop-notification")
    {
        SendToBridge(new
        {
            op = "notify",
            title = title,
            body = body,
            app_name = appName,
            urgency = urgency,
            icon = icon
        });
    }

    public void TriggerKickoff()
    {
        SendToBridge(new { op = "kickoff" });
    }

    public void TriggerKRunner()
    {
        SendToBridge(new { op = "krunner" });
    }

    public void SendVolume(int percent)
    {
        SendToBridge(new { op = "volume", percent = percent });
    }

    public void SendMediaOsd(string icon, string text)
    {
        SendToBridge(new { op = "media_osd", icon = icon, text = text });
    }

    public void SendToBridge(object message)
    {
        if (_bridgeInput == null || _disposed || _bridgeDead) return;
        try
        {
            var json = JsonSerializer.Serialize(message);
            lock (_bridgeLock)
            {
                if (_bridgeInput == null || _bridgeDead) return;
                _bridgeInput.WriteLine(json);
                _bridgeInput.Flush();
            }
        }
        catch (IOException)
        {
            // Broken pipe — bridge process died
            DiagnosticLog.Warn(LogComponent, "Broken pipe detected on SendToBridge. Triggering restart.");
            _bridgeDead = true;
            ScheduleBridgeRestart();
        }
        catch (ObjectDisposedException)
        {
            // Stream already closed
            _bridgeDead = true;
        }
        catch (Exception ex)
        {
            DiagnosticLog.Error(LogComponent, "Unexpected error in SendToBridge", ex);
        }
    }

    public sealed record ComposableWindow(nint Hwnd, string Title, string ProcessName, string AppId, uint Pid);

    public static List<ComposableWindow> EnumerateComposableWindows()
    {
        var list = new List<ComposableWindow>();
        bool ProcessHwnd(nint hwnd)
        {
            if (IsQualifyingAppWindow(hwnd, out var title, out var processName, out var appId, out var pid))
            {
                list.Add(new ComposableWindow(hwnd, title, processName, appId, pid));
            }
            return true;
        }

        nint hDesk = OpenDesktop("default", 0, false, 0x01FF);
        if (hDesk != nint.Zero)
        {
            try
            {
                EnumDesktopWindows(hDesk, (hwnd, _) => ProcessHwnd(hwnd), nint.Zero);
            }
            finally
            {
                CloseDesktop(hDesk);
            }
        }
        else
        {
            EnumWindows((hwnd, _) => ProcessHwnd(hwnd), nint.Zero);
        }

        return list;
    }

    private const int DWMWA_CLOAKED = 14;

    private void CheckAndSendFullscreenState()
    {
        try
        {
            var fg = GetForegroundWindow();
            var nowFullscreen = fg != nint.Zero && IsFullScreenWindow(fg);
            if (nowFullscreen != _anyFullscreen)
            {
                _anyFullscreen = nowFullscreen;
                SendToBridge(new { op = "fullscreen", active = nowFullscreen });
                KdePanelManager.SetFullscreenActive(nowFullscreen);
            }
        }
        catch (Exception ex)
        {
            DiagnosticLog.Warn(LogComponent, $"Fullscreen check failed: {ex.Message}");
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT
    {
        public int Left, Top, Right, Bottom;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
    private struct MONITORINFO
    {
        public int cbSize;
        public RECT rcMonitor;
        public RECT rcWork;
        public uint dwFlags;
    }

    private static bool IsFullScreenWindow(nint hwnd)
    {
        if (!IsWindow(hwnd) || IsIconic(hwnd) || !IsWindowVisible(hwnd)) return false;

        // Exclude our own process and shell windows
        GetWindowThreadProcessId(hwnd, out var fsPid);
        if (fsPid != 0)
        {
            try
            {
                using var proc = Process.GetProcessById((int)fsPid);
                var name = proc.ProcessName;
                if (string.Equals(name, "ntkde", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, "DesktopSurfaceHost", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, "explorer", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, "ShellExperienceHost", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, "msrdc", StringComparison.OrdinalIgnoreCase))
                {
                    return false;
                }
            }
            catch { }
        }

        var sbClass = new StringBuilder(256);
        GetClassName(hwnd, sbClass, 256);
        var className = sbClass.ToString();
        if (className is "Progman" or "WorkerW" or "Shell_TrayWnd" or "Shell_SecondaryTrayWnd")
            return false;

        var sbTitle = new StringBuilder(512);
        GetWindowText(hwnd, sbTitle, 512);
        var title = sbTitle.ToString();
        if (title.Contains("Desktop @", StringComparison.OrdinalIgnoreCase) ||
            title.Contains("plasmashell", StringComparison.OrdinalIgnoreCase) ||
            title.Contains("Plasma", StringComparison.OrdinalIgnoreCase) ||
            title.Contains("ntKDE", StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        if (!GetWindowRect(hwnd, out RECT rect)) return false;
        var monitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
        var mi = new MONITORINFO { cbSize = Marshal.SizeOf<MONITORINFO>() };
        if (!GetMonitorInfo(monitor, ref mi)) return false;

        var sr = mi.rcMonitor;
        return rect.Left <= sr.Left && rect.Top <= sr.Top
            && rect.Right >= sr.Right && rect.Bottom >= sr.Bottom;
    }

    public static bool IsQualifyingAppWindow(
        nint hwnd,
        out string title,
        out string processName,
        out string appId,
        out uint pid)
    {
        title = string.Empty;
        processName = string.Empty;
        appId = string.Empty;
        pid = 0;

        if (!IsWindow(hwnd) || !IsWindowVisible(hwnd)) return false;

        // Skip cloaked windows (e.g. suspended UWP apps)
        if (DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, out int cloaked, sizeof(int)) == 0 && cloaked != 0)
        {
            return false;
        }

        // Skip non-top-level windows
        var style = GetWindowLong(hwnd, GWL_STYLE);
        if ((style & WS_CHILD) != 0) return false;

        var exStyle = GetWindowLong(hwnd, GWL_EXSTYLE);
        if ((exStyle & WS_EX_TOOLWINDOW) != 0 && (exStyle & WS_EX_APPWINDOW) == 0) return false;

        // Must have non-empty title
        var sbTitle = new StringBuilder(512);
        GetWindowText(hwnd, sbTitle, 512);
        title = sbTitle.ToString().Trim();
        if (string.IsNullOrEmpty(title)) return false;

        // Class name checks
        var sbClass = new StringBuilder(256);
        GetClassName(hwnd, sbClass, 256);
        var className = sbClass.ToString();

        if (className is "Progman" or "WorkerW" or "Shell_TrayWnd" or "Shell_SecondaryTrayWnd" or
            "GDI+ Window" or "MSCTFIME UI" or "IME" or "tooltips_class32" or
            "RAIL_WINDOW" or "Cua.AgentCursorOverlay")
        {
            return false;
        }

        // Title checks
        if (title.Contains("ntKDE Wallpaper Surface", StringComparison.OrdinalIgnoreCase) ||
            title.Contains("Desktop @ QRect", StringComparison.OrdinalIgnoreCase) ||
            title.Contains("Task Switching", StringComparison.OrdinalIgnoreCase) ||
            title.Contains("Windows Input Experience", StringComparison.OrdinalIgnoreCase) ||
            (title.Contains("plasmashell", StringComparison.OrdinalIgnoreCase) && className != "Chrome_WidgetWin_1"))
        {
            return false;
        }

        // Get process info
        GetWindowThreadProcessId(hwnd, out pid);
        if (pid == 0) return false;

        try
        {
            using var proc = Process.GetProcessById((int)pid);
            processName = proc.ProcessName;
        }
        catch
        {
            processName = "app";
        }

        // Ignore our own host and non-interactive system overlay processes
        if (string.Equals(processName, "ntkde", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(processName, "DesktopSurfaceHost", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(processName, "TextInputHost", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(processName, "ShellExperienceHost", StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        appId = MapProcessNameToAppId(processName, title);
        return true;
    }

    private static string MapProcessNameToAppId(string processName, string title)
    {
        var lower = processName.ToLowerInvariant();
        return lower switch
        {
            "chrome" => "google-chrome",
            "msedge" => "microsoft-edge",
            "firefox" => "firefox",
            "code" => "code",
            "devenv" => "visual-studio",
            "notepad" => "notepad",
            "discord" => "discord",
            "spotify" => "spotify",
            "slack" => "slack",
            "steam" => "steam",
            "explorer" => "org.kde.dolphin",
            "systemsettings" => "preferences-system",
            "calculator" or "calculatorapp" => "accessories-calculator",
            "applicationframehost" => title.ToLowerInvariant() switch
            {
                var t when t.Contains("calculator") => "accessories-calculator",
                var t when t.Contains("xbox") => "applications-games",
                var t when t.Contains("settings") => "preferences-system",
                var t when t.Contains("photos") => "org.kde.gwenview",
                var t when t.Contains("paint") => "org.kde.kolourpaint",
                _ => "applicationframehost"
            },
            "cmd" or "powershell" or "windowsterminal" => "org.kde.konsole",
            _ => lower
        };
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        DiagnosticLog.Info(LogComponent, "WindowsTaskTracker disposing...");
        _periodicSyncTimer.Dispose();
        _cts.Cancel();

        if (_hook != nint.Zero)
        {
            UnhookWinEvent(_hook);
            _hook = nint.Zero;
        }

        lock (_bridgeLock)
        {
            try
            {
                _bridgeInput?.Close();
                if (_bridgeProcess != null)
                {
                    _bridgeProcess.Exited -= OnBridgeProcessExited;
                    if (!_bridgeProcess.HasExited)
                    {
                        _bridgeProcess.Kill();
                    }
                }
            }
            catch { }

            _bridgeProcess?.Dispose();
        }

        _cts.Dispose();
        _trackedTasks.Clear();
        SetBridgeStatus(BridgeState.NotStarted);
        DiagnosticLog.Info(LogComponent, "WindowsTaskTracker disposed.");
    }

    private record TrackedTask(
        nint Hwnd,
        string Title,
        string AppId,
        string ProcessName,
        uint ProcessId,
        bool IsMinimized,
        bool IsActive);

    private delegate void WinEventDelegate(
        nint hook,
        uint eventType,
        nint hwnd,
        int objectId,
        int childId,
        uint threadId,
        uint eventTime);

    private delegate bool EnumWindowsProc(nint hwnd, nint lParam);

    [DllImport("user32.dll")]
    private static extern nint SetWinEventHook(
        uint eventMin, uint eventMax, nint module, WinEventDelegate callback,
        uint processId, uint threadId, uint flags);

    [DllImport("user32.dll")]
    private static extern bool UnhookWinEvent(nint hook);

    [DllImport("user32.dll")]
    private static extern bool IsWindow(nint hwnd);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(nint hwnd);

    [DllImport("user32.dll")]
    private static extern bool IsIconic(nint hwnd);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(nint hwnd);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(nint hwnd, int nCmdShow);

    [DllImport("user32.dll")]
    private static extern nint GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern uint GetWindowLong(nint hwnd, int nIndex);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(nint hwnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(nint hwnd, StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hwnd, out uint processId);

    [DllImport("user32.dll")]
    private static extern nint OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll")]
    private static extern bool CloseDesktop(nint hDesktop);

    [DllImport("user32.dll")]
    private static extern bool EnumDesktopWindows(nint hDesktop, EnumWindowsProc lpfn, nint lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, nint lParam);

    [DllImport("dwmapi.dll")]
    private static extern int DwmGetWindowAttribute(nint hwnd, int dwAttribute, out int pvAttribute, int cbAttribute);

    [DllImport("user32.dll")]
    private static extern nint PostMessage(nint hwnd, uint msg, nint wParam, nint lParam);

    [DllImport("user32.dll")]
    private static extern void SwitchToThisWindow(nint hWnd, bool fAltTab);

    [DllImport("user32.dll")]
    private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

    [DllImport("user32.dll")]
    private static extern bool BringWindowToTop(nint hWnd);

    [DllImport("kernel32.dll")]
    private static extern uint GetCurrentThreadId();

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(nint hwnd, out RECT lpRect);

    [DllImport("user32.dll")]
    private static extern nint MonitorFromWindow(nint hwnd, uint dwFlags);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    private static extern bool GetMonitorInfo(nint hMonitor, ref MONITORINFO lpmi);
}
