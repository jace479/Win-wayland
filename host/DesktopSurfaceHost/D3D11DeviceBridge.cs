using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

internal sealed class D3D11DeviceBridge : IDisposable
{
    private const uint HardwareDriver = 1;
    private const uint SdkVersion = 7;
    private nint device;
    private nint context;

    private D3D11DeviceBridge(nint device, nint context, uint featureLevel)
    {
        this.device = device;
        this.context = context;
        FeatureLevel = featureLevel;
    }

    public uint FeatureLevel { get; }
    internal nint RawDevice => device;
    internal nint Context => context;

    public bool TryCreateStagingTexture(int width, int height, out nint stagingTexture)
    {
        stagingTexture = nint.Zero;
        if (device == nint.Zero || width <= 0 || height <= 0) return false;

        var desc = new D3D11_TEXTURE2D_DESC
        {
            Width = (uint)width,
            Height = (uint)height,
            MipLevels = 1,
            ArraySize = 1,
            Format = 87, // DXGI_FORMAT_B8G8R8A8_UNORM
            SampleDesc = new DXGI_SAMPLE_DESC { Count = 1, Quality = 0 },
            Usage = 3, // D3D11_USAGE_STAGING
            BindFlags = 0,
            CPUAccessFlags = 0x20000, // D3D11_CPU_ACCESS_READ
            MiscFlags = 0
        };

        try
        {
            var vtable = Marshal.ReadIntPtr(device);
            var createTexture2D = Marshal.GetDelegateForFunctionPointer<CreateTexture2DDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 5));
            var hr = createTexture2D(device, ref desc, nint.Zero, out stagingTexture);
            return hr >= 0 && stagingTexture != nint.Zero;
        }
        catch
        {
            stagingTexture = nint.Zero;
            return false;
        }
    }

    public void CopyResource(nint dstResource, nint srcResource)
    {
        if (context == nint.Zero || dstResource == nint.Zero || srcResource == nint.Zero) return;
        try
        {
            var vtable = Marshal.ReadIntPtr(context);
            var copyResource = Marshal.GetDelegateForFunctionPointer<CopyResourceDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 47));
            copyResource(context, dstResource, srcResource);
        }
        catch
        {
        }
    }

    public bool TryMapRead(nint resource, out D3D11_MAPPED_SUBRESOURCE mapped)
    {
        mapped = default;
        if (context == nint.Zero || resource == nint.Zero) return false;
        try
        {
            var vtable = Marshal.ReadIntPtr(context);
            var map = Marshal.GetDelegateForFunctionPointer<MapDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 14));
            var hr = map(context, resource, 0, 1 /* D3D11_MAP_READ */, 0, out mapped);
            return hr >= 0 && mapped.pData != nint.Zero;
        }
        catch
        {
            return false;
        }
    }

    public void Unmap(nint resource)
    {
        if (context == nint.Zero || resource == nint.Zero) return;
        try
        {
            var vtable = Marshal.ReadIntPtr(context);
            var unmap = Marshal.GetDelegateForFunctionPointer<UnmapDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 15));
            unmap(context, resource, 0);
        }
        catch
        {
        }
    }

    public static bool TryCreate(out D3D11DeviceBridge? bridge)
    {
        bridge = null;
        try
        {
            var result = D3D11CreateDevice(
                nint.Zero,
                HardwareDriver,
                nint.Zero,
                0,
                nint.Zero,
                0,
                SdkVersion,
                out var device,
                out var featureLevel,
                out var context);
            if (result < 0 || device == nint.Zero || context == nint.Zero)
            {
                if (device != nint.Zero) Marshal.Release(device);
                if (context != nint.Zero) Marshal.Release(context);
                return false;
            }

            bridge = new D3D11DeviceBridge(device, context, featureLevel);
            return true;
        }
        catch (DllNotFoundException)
        {
            return false;
        }
        catch (EntryPointNotFoundException)
        {
            return false;
        }
    }

    public void Dispose()
    {
        if (context != nint.Zero)
        {
            Marshal.Release(context);
            context = nint.Zero;
        }
        if (device != nint.Zero)
        {
            Marshal.Release(device);
            device = nint.Zero;
        }
        GC.SuppressFinalize(this);
    }

    [DllImport("d3d11.dll")]
    private static extern int D3D11CreateDevice(
        nint adapter,
        uint driverType,
        nint software,
        uint flags,
        nint featureLevels,
        uint featureLevelsCount,
        uint sdkVersion,
        out nint device,
        out uint featureLevel,
        out nint immediateContext);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int CreateTexture2DDelegate(
        nint device,
        ref D3D11_TEXTURE2D_DESC desc,
        nint initialData,
        out nint texture2D);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate void CopyResourceDelegate(
        nint context,
        nint dstResource,
        nint srcResource);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int MapDelegate(
        nint context,
        nint resource,
        uint subresource,
        uint mapType,
        uint mapFlags,
        out D3D11_MAPPED_SUBRESOURCE mappedResource);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate void UnmapDelegate(
        nint context,
        nint resource,
        uint subresource);
}

[StructLayout(LayoutKind.Sequential)]
internal struct D3D11_TEXTURE2D_DESC
{
    public uint Width;
    public uint Height;
    public uint MipLevels;
    public uint ArraySize;
    public uint Format;
    public DXGI_SAMPLE_DESC SampleDesc;
    public uint Usage;
    public uint BindFlags;
    public uint CPUAccessFlags;
    public uint MiscFlags;
}

[StructLayout(LayoutKind.Sequential)]
internal struct DXGI_SAMPLE_DESC
{
    public uint Count;
    public uint Quality;
}

[StructLayout(LayoutKind.Sequential)]
internal struct D3D11_MAPPED_SUBRESOURCE
{
    public nint pData;
    public uint RowPitch;
    public uint DepthPitch;
}