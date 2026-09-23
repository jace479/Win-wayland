using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Text;

namespace NtPlasma.DesktopSurfaceHost;

internal sealed class WindowCaptureStreamer : IDisposable
{
    private const int MagicNtfr = 0x4E545246; // "NTFR" in ASCII
    private const uint PwRenderFullContent = 2;
    private const uint WmMousMove = 0x0200;
    private const uint WmLButtonDown = 0x0201;
    private const uint WmLButtonUp = 0x0202;
    private const uint WmLButtonDblClk = 0x0203;
    private const uint WmRButtonDown = 0x0204;
    private const uint WmRButtonUp = 0x0205;
    private const uint WmRButtonDblClk = 0x0206;
    private const uint WmMouseWheel = 0x020A;
    private const uint WmKeyDown = 0x0100;
    private const uint WmKeyUp = 0x0101;
    private const uint WmChar = 0x0102;
    private const uint WmClose = 0x0010;

    private const uint SwpNomove = 0x0002;
    private const uint SwpNozorder = 0x0004;
    private const uint SwpNoactivate = 0x0010;

    private const int SwMaximize = 3;
    private const int SwMinimize = 6;
    private const int SwRestore = 9;

    private readonly CancellationTokenSource cts = new();
    private nint targetHwnd;
    private string windowTitle = "Windows Application";
    private bool isRunning;
    private D3D11DeviceBridge? d3dBridge;
    private NativeCaptureSession? wgcSession;
    private nint lastCapturedHwnd;
    private nint lastAttemptedHwnd;
    private DateTime lastAttemptTime = DateTime.MinValue;
    private Task? activeSessionTask;
    private NamedPipeServerStream? activePipeServer;

    [StructLayout(LayoutKind.Sequential)]
    private struct Rect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT
    {
        public int X;
        public int Y;
    }

    private const uint MOUSEEVENTF_MOVE = 0x0001;
    private const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    private const uint MOUSEEVENTF_LEFTUP = 0x0004;
    private const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
    private const uint MOUSEEVENTF_RIGHTUP = 0x0010;
    private const uint MOUSEEVENTF_WHEEL = 0x0800;

    private const uint KEYEVENTF_KEYUP = 0x0002;
    private const uint KEYEVENTF_UNICODE = 0x0004;
    private const uint INPUT_KEYBOARD = 1;

    [StructLayout(LayoutKind.Sequential)]
    private struct KEYBDINPUT
    {
        public ushort wVk;
        public ushort wScan;
        public uint dwFlags;
        public uint time;
        public nint dwExtraInfo;
    }

    [StructLayout(LayoutKind.Explicit)]
    private struct InputUnion
    {
        [FieldOffset(0)]
        public KEYBDINPUT ki;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct INPUT
    {
        public uint type;
        public InputUnion u;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

    [DllImport("user32.dll")]
    private static extern bool ClientToScreen(nint hWnd, ref POINT lpPoint);

    [DllImport("user32.dll")]
    private static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll")]
    private static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, nint dwExtraInfo);

    [DllImport("user32.dll")]
    private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, nint dwExtraInfo);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    private static extern nint GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

    [DllImport("user32.dll")]
    private static extern nint SetFocus(nint hWnd);

    [DllImport("kernel32.dll")]
    private static extern uint GetCurrentThreadId();

    [DllImport("user32.dll")]
    private static extern bool IsWindow(nint window);

    [DllImport("user32.dll")]
    private static extern bool GetClientRect(nint window, out Rect clientRect);

    [DllImport("user32.dll")]
    private static extern bool PrintWindow(nint window, nint hdcBlt, uint nFlags);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(nint window);

    [DllImport("user32.dll")]
    private static extern nint PostMessage(nint window, uint message, nint wParam, nint lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(nint window, StringBuilder text, int length);

    [DllImport("user32.dll")]
    private static extern bool SetWindowPos(nint hWnd, nint hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(nint hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    private static extern bool IsIconic(nint hWnd);

    private void ActivateTargetWindow()
    {
        if (targetHwnd == nint.Zero || !IsWindow(targetHwnd)) return;

        var fgHwnd = GetForegroundWindow();
        if (fgHwnd == targetHwnd) return;

        var fgThread = GetWindowThreadProcessId(fgHwnd, out _);
        var curThread = GetCurrentThreadId();

        if (fgThread != curThread && fgThread != 0)
        {
            AttachThreadInput(curThread, fgThread, true);
            SetForegroundWindow(targetHwnd);
            SetFocus(targetHwnd);
            AttachThreadInput(curThread, fgThread, false);
        }
        else
        {
            SetForegroundWindow(targetHwnd);
            SetFocus(targetHwnd);
        }
    }

    private static void SendUnicodeText(string text)
    {
        if (string.IsNullOrEmpty(text)) return;
        var inputs = new INPUT[text.Length * 2];
        for (var i = 0; i < text.Length; i++)
        {
            inputs[i * 2] = new INPUT
            {
                type = INPUT_KEYBOARD,
                u = new InputUnion
                {
                    ki = new KEYBDINPUT
                    {
                        wVk = 0,
                        wScan = text[i],
                        dwFlags = KEYEVENTF_UNICODE
                    }
                }
            };
            inputs[i * 2 + 1] = new INPUT
            {
                type = INPUT_KEYBOARD,
                u = new InputUnion
                {
                    ki = new KEYBDINPUT
                    {
                        wVk = 0,
                        wScan = text[i],
                        dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                    }
                }
            };
        }
        SendInput((uint)inputs.Length, inputs, Marshal.SizeOf<INPUT>());
    }

    public WindowCaptureStreamer()
    {
    }

    public void Start(nint initialHwnd = default)
    {
        if (isRunning) return;
        isRunning = true;
        SetTargetHwnd(initialHwnd);
    }

    public void SetTargetHwnd(nint hwnd)
    {
        targetHwnd = hwnd;
        if (hwnd != nint.Zero && IsWindow(hwnd))
        {
            if (IsIconic(hwnd))
            {
                ShowWindow(hwnd, SwRestore);
            }
            var sb = new StringBuilder(256);
            GetWindowText(hwnd, sb, sb.Capacity);
            windowTitle = sb.Length > 0 ? sb.ToString() : "Windows Application";
            EnsureCaptureSession(hwnd);
        }
        else
        {
            ResetCaptureSession();
        }
    }

    private void EnsureCaptureSession(nint hwnd)
    {
        if (hwnd == lastCapturedHwnd && wgcSession != null && wgcSession.IsRunning) return;
        if (hwnd == lastAttemptedHwnd && (DateTime.UtcNow - lastAttemptTime).TotalSeconds < 3.0)
        {
            return;
        }

        lastAttemptedHwnd = hwnd;
        lastAttemptTime = DateTime.UtcNow;

        ResetCaptureSession();
        lastCapturedHwnd = hwnd;

        try
        {
            if (d3dBridge == null)
            {
                D3D11DeviceBridge.TryCreate(out d3dBridge);
            }

            if (d3dBridge != null && hwnd != nint.Zero)
            {
                GetClientRect(hwnd, out var rect);
                var width = Math.Max(1, rect.Right - rect.Left);
                var height = Math.Max(1, rect.Bottom - rect.Top);
                NativeCaptureSession.TryStart(hwnd, d3dBridge, width, height, out wgcSession);
            }
        }
        catch
        {
            wgcSession = null;
        }
    }

    private void ResetCaptureSession()
    {
        wgcSession?.Dispose();
        wgcSession = null;
        lastCapturedHwnd = nint.Zero;
    }

    public void StartPipedSession(Stream inputStream, Stream outputStream)
    {
        activeSessionTask = Task.Run(() => StreamSessionAsync(inputStream, outputStream, cts.Token));
    }

    public void StartNamedPipeServer(string pipeName = "ntkde_surface")
    {
        activeSessionTask = Task.Run(async () =>
        {
            while (!cts.IsCancellationRequested)
            {
                try
                {
                    activePipeServer = new NamedPipeServerStream(
                        pipeName,
                        PipeDirection.InOut,
                        1,
                        PipeTransmissionMode.Byte,
                        PipeOptions.Asynchronous);

                    await activePipeServer.WaitForConnectionAsync(cts.Token);
                    await StreamSessionAsync(activePipeServer, activePipeServer, cts.Token);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Trace.WriteLine($"Named pipe session error: {ex.Message}");
                    try
                    {
                        await Task.Delay(500, cts.Token);
                    }
                    catch (OperationCanceledException)
                    {
                        break;
                    }
                }
                finally
                {
                    activePipeServer?.Dispose();
                    activePipeServer = null;
                }
            }
        }, cts.Token);
    }

    public async Task StreamSessionAsync(Stream inputStream, Stream outputStream, CancellationToken token = default)
    {
        using var reader = new StreamReader(inputStream, Encoding.UTF8, leaveOpen: true);

        // Start background reader task for incoming input events across pipe
        var inputTask = Task.Run(async () =>
        {
            try
            {
                while (!token.IsCancellationRequested)
                {
                    var line = await reader.ReadLineAsync(token);
                    if (line is null) break;
                    ProcessInputCommand(line);
                }
            }
            catch { }
        }, token);

        var header = new byte[20];
        while (!token.IsCancellationRequested)
        {
            if (targetHwnd == nint.Zero || !IsWindow(targetHwnd))
            {
                await Task.Delay(200, token);
                continue;
            }

            if (IsIconic(targetHwnd))
            {
                ShowWindow(targetHwnd, SwRestore);
            }

            EnsureCaptureSession(targetHwnd);

            byte[]? pixels = null;
            int width = 0, height = 0;

            try
            {
                if (wgcSession != null && wgcSession.IsRunning)
                {
                    pixels = wgcSession.TryAcquireFramePixels(out width, out height);
                }
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"WGC acquire error: {ex.Message}");
                pixels = null;
            }

            try
            {
                if (pixels == null || pixels.Length == 0)
                {
                    pixels = CaptureWindowPixels(targetHwnd, out width, out height);
                }
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"Fallback GDI capture error: {ex.Message}");
                pixels = null;
            }

            if (pixels is not null && pixels.Length > 0)
            {
                // Write NTFR Header:
                // int32 monitor/id (1)
                // int32 width
                // int32 height
                // int32 payloadLength
                // int32 magic (0x4E545246)
                BitConverter.TryWriteBytes(header.AsSpan(0, 4), 1);
                BitConverter.TryWriteBytes(header.AsSpan(4, 4), width);
                BitConverter.TryWriteBytes(header.AsSpan(8, 4), height);
                BitConverter.TryWriteBytes(header.AsSpan(12, 4), pixels.Length);
                BitConverter.TryWriteBytes(header.AsSpan(16, 4), MagicNtfr);

                try
                {
                    await outputStream.WriteAsync(header, 0, header.Length, token);
                    await outputStream.WriteAsync(pixels, 0, pixels.Length, token);
                    await outputStream.FlushAsync(token);
                }
                catch (Exception)
                {
                    break;
                }
            }

            await Task.Delay(33, token); // ~30 FPS frame cadence
        }

        try { await inputTask; } catch { }
    }

    public static byte[]? CaptureWindowPixels(nint hwnd, out int width, out int height)
    {
        if (hwnd == nint.Zero || !IsWindow(hwnd))
        {
            width = height = 0;
            return null;
        }

        if (IsIconic(hwnd))
        {
            ShowWindow(hwnd, SwRestore);
        }

        GetClientRect(hwnd, out var rect);
        var rawW = rect.Right - rect.Left;
        var rawH = rect.Bottom - rect.Top;
        width = Math.Max(rawW > 0 ? rawW : 800, 1);
        height = Math.Max(rawH > 0 ? rawH : 600, 1);

        using var bitmap = new Bitmap(width, height, PixelFormat.Format24bppRgb);
        using (var graphics = Graphics.FromImage(bitmap))
        {
            var hdc = graphics.GetHdc();
            try
            {
                if (!PrintWindow(hwnd, hdc, PwRenderFullContent))
                {
                    PrintWindow(hwnd, hdc, 0);
                }
            }
            finally
            {
                graphics.ReleaseHdc(hdc);
            }
        }

        var data = bitmap.LockBits(
            new Rectangle(0, 0, width, height),
            ImageLockMode.ReadOnly,
            PixelFormat.Format24bppRgb);
        try
        {
            var stride = Math.Abs(data.Stride);
            var buffer = new byte[width * height * 3];
            if (stride == width * 3)
            {
                Marshal.Copy(data.Scan0, buffer, 0, buffer.Length);
            }
            else
            {
                for (var y = 0; y < height; y++)
                {
                    var rowPtr = data.Scan0 + (y * stride);
                    Marshal.Copy(rowPtr, buffer, y * width * 3, width * 3);
                }
            }
            return buffer;
        }
        finally
        {
            bitmap.UnlockBits(data);
        }
    }

    private void ProcessInputCommand(string command)
    {
        if (string.IsNullOrWhiteSpace(command) || targetHwnd == nint.Zero || !IsWindow(targetHwnd))
        {
            return;
        }

        // Format: INPUT|<event>|<args>
        var parts = command.Split('|');
        if (parts.Length < 2) return;

        var eventType = parts[1];
        switch (eventType)
        {
            case "POINTER":
                // INPUT|POINTER|<action>|<x>|<y>|<btn_or_delta>
                if (parts.Length >= 5 &&
                    int.TryParse(parts[3], out var x) &&
                    int.TryParse(parts[4], out var y))
                {
                    var action = parts[2];
                    var pt = new POINT { X = x, Y = y };
                    ClientToScreen(targetHwnd, ref pt);

                    switch (action)
                    {
                        case "move":
                            SetCursorPos(pt.X, pt.Y);
                            break;

                        case "press":
                            ActivateTargetWindow();
                            SetCursorPos(pt.X, pt.Y);
                            var isRight = parts.Length > 5 && parts[5] == "right";
                            mouse_event(isRight ? MOUSEEVENTF_RIGHTDOWN : MOUSEEVENTF_LEFTDOWN, 0, 0, 0, nint.Zero);
                            break;

                        case "release":
                            var isRightR = parts.Length > 5 && parts[5] == "right";
                            mouse_event(isRightR ? MOUSEEVENTF_RIGHTUP : MOUSEEVENTF_LEFTUP, 0, 0, 0, nint.Zero);
                            break;

                        case "dblclk":
                            ActivateTargetWindow();
                            SetCursorPos(pt.X, pt.Y);
                            var isRightD = parts.Length > 5 && parts[5] == "right";
                            var down = isRightD ? MOUSEEVENTF_RIGHTDOWN : MOUSEEVENTF_LEFTDOWN;
                            var up = isRightD ? MOUSEEVENTF_RIGHTUP : MOUSEEVENTF_LEFTUP;
                            mouse_event(down, 0, 0, 0, nint.Zero);
                            mouse_event(up, 0, 0, 0, nint.Zero);
                            mouse_event(down, 0, 0, 0, nint.Zero);
                            mouse_event(up, 0, 0, 0, nint.Zero);
                            break;

                        case "wheel":
                            SetCursorPos(pt.X, pt.Y);
                            var delta = parts.Length > 5 && int.TryParse(parts[5], out var d) ? d : 120;
                            mouse_event(MOUSEEVENTF_WHEEL, 0, 0, (uint)delta, nint.Zero);
                            break;
                    }
                }
                break;

            case "KEY":
                // INPUT|KEY|<action>|<virtualKey>
                if (parts.Length >= 4 && int.TryParse(parts[3], out var vk))
                {
                    ActivateTargetWindow();
                    var keyAction = parts[2];
                    if (keyAction == "press")
                    {
                        keybd_event((byte)vk, 0, 0, nint.Zero);
                    }
                    else
                    {
                        keybd_event((byte)vk, 0, KEYEVENTF_KEYUP, nint.Zero);
                    }
                }
                break;

            case "CHAR":
                // INPUT|CHAR|<character>
                if (parts.Length >= 3)
                {
                    ActivateTargetWindow();
                    SendUnicodeText(parts[2]);
                }
                break;

            case "RESIZE":
                // INPUT|RESIZE|<width>|<height>
                if (parts.Length >= 4 &&
                    int.TryParse(parts[2], out var newWidth) &&
                    int.TryParse(parts[3], out var newHeight) &&
                    newWidth > 0 && newHeight > 0)
                {
                    SetWindowPos(targetHwnd, nint.Zero, 0, 0, newWidth, newHeight,
                        SwpNomove | SwpNozorder | SwpNoactivate);
                    ResetCaptureSession();
                }
                break;

            case "STATE":
                // INPUT|STATE|<minimize|maximize|restore>
                if (parts.Length >= 3)
                {
                    var state = parts[2].ToLowerInvariant();
                    var showCmd = state switch
                    {
                        "minimize" or "min" => SwMinimize,
                        "maximize" or "max" => SwMaximize,
                        "restore" => SwRestore,
                        _ => -1
                    };
                    if (showCmd >= 0)
                    {
                        ShowWindow(targetHwnd, showCmd);
                    }
                }
                break;

            case "FOCUS":
                ActivateTargetWindow();
                break;

            case "CLOSE":
                PostMessage(targetHwnd, WmClose, nint.Zero, nint.Zero);
                break;
        }
    }

    public void Dispose()
    {
        cts.Cancel();
        activePipeServer?.Dispose();
        activePipeServer = null;
        ResetCaptureSession();
        d3dBridge?.Dispose();
        d3dBridge = null;
        cts.Dispose();
    }
}
