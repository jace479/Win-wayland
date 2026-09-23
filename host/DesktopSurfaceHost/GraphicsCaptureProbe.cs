using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

internal static class GraphicsCaptureProbe
{
    public static string Describe(nint hwnd, nint d3d11Device = default)
    {
        var hwndValid = hwnd != nint.Zero && IsWindow(hwnd);
        if (!hwndValid)
        {
            return "WGC probe: no valid HWND";
        }

        if (!OperatingSystem.IsWindowsVersionAtLeast(10, 0, 18362))
        {
            return "WGC probe: Windows Graphics Capture unavailable";
        }

        var captureApiPresent = GraphicsCaptureInterop.IsAvailable();
        if (!captureApiPresent)
        {
            return "WGC probe: runtime API unavailable";
        }

        if (!GraphicsCaptureInterop.TryCreateForWindow(hwnd, out var captureItem))
        {
            return "WGC probe: CreateForWindow failed";
        }

        Marshal.Release(captureItem);
        if (!GraphicsCaptureInterop.IsFramePoolAvailable())
        {
            return "WGC probe: item acquired; frame-pool factory unavailable";
        }

        if (d3d11Device != nint.Zero)
        {
            if (GraphicsCaptureInterop.TryCreateCaptureSessionHandles(hwnd, d3d11Device, 64, 64, out var item, out var pool, out var session))
            {
                Marshal.Release(session);
                Marshal.Release(pool);
                Marshal.Release(item);
                return "WGC probe: capture session created successfully";
            }
            return "WGC probe: capture session creation failed";
        }

        return "WGC probe: frame-pool factory available; session creation ready";
    }

    [DllImport("user32.dll")]
    private static extern bool IsWindow(nint window);

}