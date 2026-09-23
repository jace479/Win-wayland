using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace NtPlasma.DesktopSurfaceHost;

public sealed class GlobalHotkeyManager : NativeWindow, IDisposable
{
    private const int WM_HOTKEY = 0x0312;
    private const uint MOD_ALT = 0x0001;
    private const uint MOD_CONTROL = 0x0002;
    private const uint MOD_SHIFT = 0x0004;
    private const uint MOD_WIN = 0x0008;
    private const uint MOD_NOREPEAT = 0x4000;

    private const int WH_KEYBOARD_LL = 13;
    private const int WM_KEYDOWN = 0x0100;
    private const int WM_KEYUP = 0x0101;
    private const int WM_SYSKEYDOWN = 0x0104;
    private const int WM_SYSKEYUP = 0x0105;
    private const int VK_LWIN = 0x5B;
    private const int VK_RWIN = 0x5C;

    public event Action? EmergencyRecovery;
    public event Action? KRunnerRequested;
    public event Action? KonsoleRequested;
    public event Action? DolphinRequested;
    public event Action? KickoffRequested;

    private delegate nint HookProc(int nCode, nint wParam, nint lParam);

    [StructLayout(LayoutKind.Sequential)]
    private struct KBDLLHOOKSTRUCT
    {
        public uint vkCode;
        public uint scanCode;
        public uint flags;
        public uint time;
        public nint dwExtraInfo;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern nint SetWindowsHookEx(int idHook, HookProc lpfn, nint hMod, uint dwThreadId);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnhookWindowsHookEx(nint hhk);

    [DllImport("user32.dll")]
    private static extern nint CallNextHookEx(nint hhk, int nCode, nint wParam, nint lParam);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern nint GetModuleHandle(string? lpModuleName);

    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(nint hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll")]
    private static extern bool UnregisterHotKey(nint hWnd, int id);

    private readonly HookProc _hookProc;
    private nint _hookHandle = nint.Zero;
    private bool _winDown = false;
    private bool _otherKeyPressed = false;

    public GlobalHotkeyManager()
    {
        CreateHandle(new CreateParams());

        // 100: Emergency Recovery (Ctrl+Alt+Shift+Esc)
        RegisterHotKey(Handle, 100, MOD_CONTROL | MOD_ALT | MOD_SHIFT, (uint)Keys.Escape);
        // 101: KRunner (Alt+Space)
        RegisterHotKey(Handle, 101, MOD_ALT | MOD_NOREPEAT, (uint)Keys.Space);
        // 102: Konsole (Win+T)
        RegisterHotKey(Handle, 102, MOD_WIN | MOD_NOREPEAT, (uint)Keys.T);
        // 103: Dolphin (Win+E)
        RegisterHotKey(Handle, 103, MOD_WIN | MOD_NOREPEAT, (uint)Keys.E);

        // Low-level keyboard hook to detect naked Super/Win key taps for KDE Kickoff
        _hookProc = LowLevelKeyboardCallback;
        using var curProcess = Process.GetCurrentProcess();
        using var curModule = curProcess.MainModule;
        var modHandle = GetModuleHandle(curModule?.ModuleName);
        _hookHandle = SetWindowsHookEx(WH_KEYBOARD_LL, _hookProc, modHandle, 0);
    }

    private nint LowLevelKeyboardCallback(int nCode, nint wParam, nint lParam)
    {
        if (nCode >= 0)
        {
            var msg = wParam.ToInt32();
            var info = Marshal.PtrToStructure<KBDLLHOOKSTRUCT>(lParam);
            var vk = (int)info.vkCode;

            if (msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN)
            {
                if (vk == VK_LWIN || vk == VK_RWIN)
                {
                    _winDown = true;
                    _otherKeyPressed = false;
                }
                else if (_winDown)
                {
                    _otherKeyPressed = true;
                }
            }
            else if (msg == WM_KEYUP || msg == WM_SYSKEYUP)
            {
                if (vk == VK_LWIN || vk == VK_RWIN)
                {
                    if (_winDown && !_otherKeyPressed)
                    {
                        try
                        {
                            KickoffRequested?.Invoke();
                        }
                        catch (Exception ex)
                        {
                            Trace.WriteLine($"Error triggering Kickoff: {ex.Message}");
                        }
                    }
                    _winDown = false;
                    _otherKeyPressed = false;
                }
            }
        }

        return CallNextHookEx(_hookHandle, nCode, wParam, lParam);
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_HOTKEY)
        {
            switch (m.WParam.ToInt32())
            {
                case 100:
                    EmergencyRecovery?.Invoke();
                    break;
                case 101:
                    KRunnerRequested?.Invoke();
                    break;
                case 102:
                    KonsoleRequested?.Invoke();
                    break;
                case 103:
                    DolphinRequested?.Invoke();
                    break;
            }
            return;
        }
        base.WndProc(ref m);
    }

    public void Dispose()
    {
        if (_hookHandle != nint.Zero)
        {
            UnhookWindowsHookEx(_hookHandle);
            _hookHandle = nint.Zero;
        }

        for (var i = 100; i <= 103; i++)
        {
            UnregisterHotKey(Handle, i);
        }
        DestroyHandle();
    }
}
