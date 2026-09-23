using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

internal static class Direct3D12Probe
{
    private const uint FeatureLevel11 = 0xB000;
    private static readonly Guid DeviceIid = new("189819F1-1DB6-4B57-BE54-1821339B85F7");

    public static string Describe()
    {
        if (!OperatingSystem.IsWindows())
        {
            return "D3D12: Windows unavailable";
        }

        try
        {
            var deviceIid = DeviceIid;
            var result = D3D12CreateDevice(
                nint.Zero,
                FeatureLevel11,
                ref deviceIid,
                out var device);
            if (result < 0 || device == nint.Zero)
            {
                return $"D3D12: unavailable HRESULT=0x{result:X8}";
            }

            Marshal.Release(device);
            return "D3D12: hardware device available";
        }
        catch (DllNotFoundException)
        {
            return "D3D12: runtime unavailable";
        }
        catch (EntryPointNotFoundException)
        {
            return "D3D12: entry point unavailable";
        }
    }

    [DllImport("d3d12.dll")]
    private static extern int D3D12CreateDevice(
        nint adapter,
        uint minimumFeatureLevel,
        ref Guid riid,
        out nint device);
}