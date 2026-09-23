using System.Diagnostics;
using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

internal sealed class NativeWindowEventWatcher : IDisposable
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

    private readonly string? processName;
    private readonly WinEventDelegate callback;
    private nint hook;

    public NativeWindowEventWatcher(string? processName)
    {
        this.processName = string.IsNullOrWhiteSpace(processName)
            ? null
            : Path.GetFileNameWithoutExtension(processName);
        callback = OnWinEvent;
        hook = SetWinEventHook(
            EventMin,
            EventMax,
            nint.Zero,
            callback,
            0,
            0,
            WinEventOutOfContext | WinEventSkipOwnProcess);
    }

    public event EventHandler<NativeWindowEvent>? WindowEvent;

    public void Dispose()
    {
        if (hook != nint.Zero)
        {
            UnhookWinEvent(hook);
            hook = nint.Zero;
        }
        GC.SuppressFinalize(this);
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
        if (hwnd == nint.Zero || objectId != 0 || childId != 0 || !IsWindow(hwnd) || !IsWindowVisible(hwnd))
        {
            return;
        }

        GetWindowThreadProcessId(hwnd, out var processId);
        if (!MatchesProcess(processId))
        {
            return;
        }

        WindowEvent?.Invoke(this, new NativeWindowEvent(hwnd, MapEvent(eventType), processId));
    }

    private bool MatchesProcess(uint processId)
    {
        if (processName is null)
        {
            return true;
        }

        try
        {
            using var process = Process.GetProcessById((int)processId);
            return string.Equals(process.ProcessName, processName, StringComparison.OrdinalIgnoreCase);
        }
        catch (ArgumentException)
        {
            return false;
        }
    }

    private static string MapEvent(uint eventType) => eventType switch
    {
        EventObjectShow => "window.created",
        EventObjectHide => "window.destroyed",
        EventObjectLocationChange => "window.updated",
        EventObjectNameChange => "window.updated",
        EventSystemForeground => "window.focused",
        _ => "window.updated",
    };

    private delegate void WinEventDelegate(
        nint hook,
        uint eventType,
        nint hwnd,
        int objectId,
        int childId,
        uint threadId,
        uint eventTime);

    [DllImport("user32.dll")]
    private static extern nint SetWinEventHook(
        uint eventMin,
        uint eventMax,
        nint module,
        WinEventDelegate callback,
        uint processId,
        uint threadId,
        uint flags);

    [DllImport("user32.dll")]
    private static extern bool UnhookWinEvent(nint hook);

    [DllImport("user32.dll")]
    private static extern bool IsWindow(nint hwnd);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(nint hwnd);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hwnd, out uint processId);
}

internal sealed record NativeWindowEvent(nint Hwnd, string Kind, uint ProcessId);