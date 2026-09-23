namespace NtPlasma.DesktopSurfaceHost;

internal sealed class NativeCaptureSession : IDisposable
{
    private readonly D3D11DeviceBridge? bridge;
    private int framesObserved;
    private bool disposed;
    private nint captureItem;
    private nint framePool;
    private nint captureSession;
    private nint stagingTexture;
    private int cachedStagingWidth;
    private int cachedStagingHeight;

    private NativeCaptureSession(D3D11DeviceBridge? bridge, nint captureItem, nint framePool, nint captureSession)
    {
        this.bridge = bridge;
        this.captureItem = captureItem;
        this.framePool = framePool;
        this.captureSession = captureSession;
    }

    public int FramesObserved => Volatile.Read(ref framesObserved);
    public bool IsRunning => !disposed && captureSession != nint.Zero;
    public event EventHandler? FrameArrived;

    internal void ObserveFrame()
    {
        if (disposed) return;
        Interlocked.Increment(ref framesObserved);
        FrameArrived?.Invoke(this, EventArgs.Empty);
    }

    public byte[]? TryAcquireFramePixels(out int width, out int height)
    {
        width = height = 0;
        if (disposed || framePool == nint.Zero || bridge == null) return null;

        try
        {
            if (!GraphicsCaptureInterop.TryGetNextFrame(framePool, out var frame))
            {
                return null;
            }

            try
            {
                if (!GraphicsCaptureInterop.TryGetFrameTexture(frame, out var texture2D, out var frameWidth, out var frameHeight))
                {
                    return null;
                }

                try
                {
                    width = frameWidth;
                    height = frameHeight;
                    var pixels = GraphicsCaptureInterop.ReadbackPixelsFromTexture(
                        bridge,
                        texture2D,
                        width,
                        height,
                        ref stagingTexture,
                        ref cachedStagingWidth,
                        ref cachedStagingHeight);

                    if (pixels != null)
                    {
                        Interlocked.Increment(ref framesObserved);
                    }
                    return pixels;
                }
                finally
                {
                    System.Runtime.InteropServices.Marshal.Release(texture2D);
                }
            }
            finally
            {
                System.Runtime.InteropServices.Marshal.Release(frame);
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Trace.WriteLine($"WGC acquire error: {ex.Message}");
            width = height = 0;
            return null;
        }
    }

    public static bool TryStart(nint hwnd, D3D11DeviceBridge bridge, int initialWidth, int initialHeight, out NativeCaptureSession? session)
    {
        session = null;
        if (hwnd == nint.Zero || bridge == null) return false;
        var width = Math.Max(1, initialWidth);
        var height = Math.Max(1, initialHeight);

        if (!GraphicsCaptureInterop.TryCreateCaptureSessionHandles(
            hwnd, bridge.RawDevice, width, height,
            out var captureItem, out var framePool, out var captureSession))
        {
            return false;
        }

        session = new NativeCaptureSession(bridge, captureItem, framePool, captureSession);
        return true;
    }

    public static bool TryStart(nint hwnd, nint d3d11Device, out NativeCaptureSession? session)
    {
        session = null;
        if (!GraphicsCaptureInterop.TryCreateCaptureSessionHandles(
            hwnd, d3d11Device, 1, 1,
            out var captureItem, out var framePool, out var captureSession))
        {
            return false;
        }

        session = new NativeCaptureSession(null, captureItem, framePool, captureSession);
        return true;
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        Release(ref stagingTexture);
        Release(ref captureSession);
        Release(ref framePool);
        Release(ref captureItem);
        GC.SuppressFinalize(this);
    }

    private static void Release(ref nint value)
    {
        if (value == nint.Zero) return;
        System.Runtime.InteropServices.Marshal.Release(value);
        value = nint.Zero;
    }
}