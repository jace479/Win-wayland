using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

internal static class GraphicsCaptureInterop
{
    private const string GraphicsCaptureItemClass = "Windows.Graphics.Capture.GraphicsCaptureItem";
    private const string CaptureFramePoolClass = "Windows.Graphics.Capture.Direct3D11CaptureFramePool";
    private static readonly Guid ActivationFactoryIid = new("00000035-0000-0000-C000-000000000046");
    private static readonly Guid GraphicsCaptureItemInteropIid = new("3628e81b-3cac-4c60-b7f4-23ce0e0c3356");
    private static readonly Guid FramePoolStaticsIid = new("7784056A-67AA-4D53-AE54-1088D5A8CA21");
    private static readonly Guid DxgiDeviceIid = new("54EC77FA-1377-44E6-8C32-88FD5F44C84C");
    private static readonly Guid Direct3DDeviceIid = new("A37624AB-8D5F-4650-9D3E-9D5D6C5E5B5A");
    private static readonly Guid DxgiInterfaceAccessIid = new("A9B3D012-3DF2-4EE3-B8D1-8695F457D3C1");
    private static readonly Guid D3D11Texture2DIid = new("6f15af34-7671-4947-8098-b8c773c80196");

    public static bool TryCreateFramePool(
        nint hwnd,
        nint d3d11Device,
        int width,
        int height,
        out nint framePool)
    {
        framePool = nint.Zero;
        nint dxgiDevice = nint.Zero;
        nint direct3DDevice = nint.Zero;
        nint className = nint.Zero;
        nint factory = nint.Zero;
        try
        {
            var dxgiIid = DxgiDeviceIid;
            if (Marshal.QueryInterface(d3d11Device, ref dxgiIid, out dxgiDevice) != 0) return false;
            if (CreateDirect3D11DeviceFromDXGIDevice(dxgiDevice, out direct3DDevice) < 0) return false;
            if (WindowsCreateString(CaptureFramePoolClass, (uint)CaptureFramePoolClass.Length, out className) < 0) return false;
            var activationIid = ActivationFactoryIid;
            if (RoGetActivationFactory(className, ref activationIid, out var activationFactory) < 0) return false;
            factory = activationFactory;
            var staticsIid = FramePoolStaticsIid;
            if (Marshal.QueryInterface(factory, ref staticsIid, out var statics) != 0) return false;
            try
            {
                var vtable = Marshal.ReadIntPtr(statics);
                var create = Marshal.GetDelegateForFunctionPointer<CreateFramePoolDelegate>(
                    Marshal.ReadIntPtr(vtable, IntPtr.Size * 6));
                var size = new SizeInt32(width, height);
                var result = create(statics, direct3DDevice, 87, 2, size, out framePool);
                return result >= 0 && framePool != nint.Zero;
            }
            finally { Marshal.Release(statics); }
        }
        finally
        {
            if (factory != nint.Zero) Marshal.Release(factory);
            if (className != nint.Zero) WindowsDeleteString(className);
            if (direct3DDevice != nint.Zero) Marshal.Release(direct3DDevice);
            if (dxgiDevice != nint.Zero) Marshal.Release(dxgiDevice);
        }
    }

    public static bool TryCreateCaptureSession(
        nint hwnd,
        nint d3d11Device,
        int width,
        int height)
    {
        var created = TryCreateCaptureSessionHandles(hwnd, d3d11Device, width, height,
            out var captureItem, out var framePool, out var captureSession);
        ReleaseSessionHandles(captureItem, framePool, captureSession);
        return created;
    }

    public static bool TryCreateCaptureSessionHandles(
        nint hwnd,
        nint d3d11Device,
        int width,
        int height,
        out nint captureItem,
        out nint framePool,
        out nint captureSession)
    {
        captureItem = nint.Zero;
        framePool = nint.Zero;
        captureSession = nint.Zero;
        if (!TryCreateForWindow(hwnd, out captureItem)) return false;
        if (!TryCreateFramePool(hwnd, d3d11Device, width, height, out framePool))
        {
            Marshal.Release(captureItem);
            captureItem = nint.Zero;
            return false;
        }

        try
        {
            var vtable = Marshal.ReadIntPtr(framePool);
            var createSession = Marshal.GetDelegateForFunctionPointer<CreateCaptureSessionDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 10));
            var result = createSession(framePool, captureItem, out captureSession);
            if (result < 0 || captureSession == nint.Zero)
            {
                ReleaseSessionHandles(captureItem, framePool, captureSession);
                captureItem = framePool = captureSession = nint.Zero;
                return false;
            }

            var sessionVtable = Marshal.ReadIntPtr(captureSession);
            var startCapture = Marshal.GetDelegateForFunctionPointer<StartCaptureDelegate>(
                Marshal.ReadIntPtr(sessionVtable, IntPtr.Size * 6));
            if (startCapture(captureSession) < 0)
            {
                ReleaseSessionHandles(captureItem, framePool, captureSession);
                captureItem = framePool = captureSession = nint.Zero;
                return false;
            }
            return true;
        }
        catch
        {
            ReleaseSessionHandles(captureItem, framePool, captureSession);
            captureItem = framePool = captureSession = nint.Zero;
            return false;
        }
    }

    public static bool TryGetNextFrame(nint framePool, out nint frame)
    {
        frame = nint.Zero;
        if (framePool == nint.Zero) return false;
        try
        {
            var vtable = Marshal.ReadIntPtr(framePool);
            var getFrame = Marshal.GetDelegateForFunctionPointer<TryGetNextFrameDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 7));
            var hr = getFrame(framePool, out frame);
            return hr >= 0 && frame != nint.Zero;
        }
        catch
        {
            frame = nint.Zero;
            return false;
        }
    }

    public static bool TryGetFrameTexture(nint frame, out nint texture2D, out int width, out int height)
    {
        texture2D = nint.Zero;
        width = height = 0;
        if (frame == nint.Zero) return false;

        nint surface = nint.Zero;
        nint dxgiAccess = nint.Zero;
        try
        {
            var frameVtable = Marshal.ReadIntPtr(frame);
            var getSize = Marshal.GetDelegateForFunctionPointer<GetContentSizeDelegate>(
                Marshal.ReadIntPtr(frameVtable, IntPtr.Size * 8));
            if (getSize(frame, out var size) >= 0)
            {
                width = size.Width;
                height = size.Height;
            }

            var getSurface = Marshal.GetDelegateForFunctionPointer<GetSurfaceDelegate>(
                Marshal.ReadIntPtr(frameVtable, IntPtr.Size * 6));
            if (getSurface(frame, out surface) < 0 || surface == nint.Zero) return false;

            var dxgiAccessIid = DxgiInterfaceAccessIid;
            if (Marshal.QueryInterface(surface, ref dxgiAccessIid, out dxgiAccess) != 0 || dxgiAccess == nint.Zero)
            {
                return false;
            }

            var accessVtable = Marshal.ReadIntPtr(dxgiAccess);
            var getInterface = Marshal.GetDelegateForFunctionPointer<GetInterfaceDelegate>(
                Marshal.ReadIntPtr(accessVtable, IntPtr.Size * 3));
            var texIid = D3D11Texture2DIid;
            var hr = getInterface(dxgiAccess, ref texIid, out texture2D);
            return hr >= 0 && texture2D != nint.Zero;
        }
        catch
        {
            if (texture2D != nint.Zero)
            {
                Marshal.Release(texture2D);
                texture2D = nint.Zero;
            }
            return false;
        }
        finally
        {
            if (dxgiAccess != nint.Zero) Marshal.Release(dxgiAccess);
            if (surface != nint.Zero) Marshal.Release(surface);
        }
    }

    public static byte[]? ReadbackPixelsFromTexture(
        D3D11DeviceBridge bridge,
        nint sourceTexture,
        int width,
        int height,
        ref nint stagingTexture,
        ref int cachedStagingWidth,
        ref int cachedStagingHeight)
    {
        if (bridge == null || sourceTexture == nint.Zero || width <= 0 || height <= 0) return null;

        if (stagingTexture == nint.Zero || cachedStagingWidth != width || cachedStagingHeight != height)
        {
            if (stagingTexture != nint.Zero)
            {
                Marshal.Release(stagingTexture);
                stagingTexture = nint.Zero;
            }
            if (!bridge.TryCreateStagingTexture(width, height, out stagingTexture))
            {
                return null;
            }
            cachedStagingWidth = width;
            cachedStagingHeight = height;
        }

        bridge.CopyResource(stagingTexture, sourceTexture);

        if (!bridge.TryMapRead(stagingTexture, out var mapped))
        {
            return null;
        }

        try
        {
            var bytes = new byte[width * height * 3];
            unsafe
            {
                var pSrcBase = (byte*)mapped.pData;
                fixed (byte* pDstBase = bytes)
                {
                    var pDst = pDstBase;
                    for (var y = 0; y < height; y++)
                    {
                        var pSrcRow = pSrcBase + (y * mapped.RowPitch);
                        for (var x = 0; x < width; x++)
                        {
                            *pDst++ = *pSrcRow++; // B
                            *pDst++ = *pSrcRow++; // G
                            *pDst++ = *pSrcRow++; // R
                            pSrcRow++;            // skip A
                        }
                    }
                }
            }
            return bytes;
        }
        finally
        {
            bridge.Unmap(stagingTexture);
        }
    }

    private static bool ReleaseSessionHandles(nint captureItem, nint framePool, nint captureSession)
    {
        if (captureSession != nint.Zero) Marshal.Release(captureSession);
        if (framePool != nint.Zero) Marshal.Release(framePool);
        if (captureItem != nint.Zero) Marshal.Release(captureItem);
        return true;
    }

    public static bool TryCreateForWindow(nint hwnd, out nint captureItem)
    {
        captureItem = nint.Zero;
        if (hwnd == nint.Zero)
        {
            return false;
        }

        nint className = nint.Zero;
        nint activationFactory = nint.Zero;
        nint interop = nint.Zero;
        try
        {
            if (WindowsCreateString(GraphicsCaptureItemClass, (uint)GraphicsCaptureItemClass.Length, out className) < 0)
            {
                return false;
            }

            var activationFactoryIid = ActivationFactoryIid;
            if (RoGetActivationFactory(className, ref activationFactoryIid, out activationFactory) < 0)
            {
                return false;
            }

            var interopIid = GraphicsCaptureItemInteropIid;
            if (Marshal.QueryInterface(activationFactory, ref interopIid, out interop) != 0)
            {
                return false;
            }

            var vtable = Marshal.ReadIntPtr(interop);
            var createForWindow = Marshal.GetDelegateForFunctionPointer<CreateForWindowDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 3));
            var itemIid = new Guid("79C3F95B-31F7-4EC2-A464-632EF5D30760");
            return createForWindow(interop, hwnd, ref itemIid, out captureItem) >= 0 && captureItem != nint.Zero;
        }
        catch (DllNotFoundException)
        {
            return false;
        }
        catch (EntryPointNotFoundException)
        {
            return false;
        }
        finally
        {
            if (interop != nint.Zero) Marshal.Release(interop);
            if (activationFactory != nint.Zero) Marshal.Release(activationFactory);
            if (className != nint.Zero) WindowsDeleteString(className);
        }
    }

    public static bool IsAvailable()
    {
        nint className = nint.Zero;
        nint activationFactory = nint.Zero;
        nint interop = nint.Zero;
        var activationFactoryIid = ActivationFactoryIid;
        var graphicsCaptureItemInteropIid = GraphicsCaptureItemInteropIid;
        try
        {
            var result = WindowsCreateString(
                GraphicsCaptureItemClass,
                (uint)GraphicsCaptureItemClass.Length,
                out className);
            if (result < 0)
            {
                return false;
            }

            result = RoGetActivationFactory(className, ref activationFactoryIid, out activationFactory);
            if (result < 0 || activationFactory == nint.Zero)
            {
                return false;
            }

            return Marshal.QueryInterface(
                activationFactory,
                ref graphicsCaptureItemInteropIid,
                out interop) == 0 && interop != nint.Zero;
        }
        catch (DllNotFoundException)
        {
            return false;
        }
        catch (EntryPointNotFoundException)
        {
            return false;
        }
        finally
        {
            if (interop != nint.Zero)
            {
                Marshal.Release(interop);
            }
            if (activationFactory != nint.Zero)
            {
                Marshal.Release(activationFactory);
            }
            if (className != nint.Zero)
            {
                WindowsDeleteString(className);
            }
        }
    }

    public static bool IsFramePoolAvailable()
    {
        nint className = nint.Zero;
        nint activationFactory = nint.Zero;
        try
        {
            if (WindowsCreateString(CaptureFramePoolClass, (uint)CaptureFramePoolClass.Length, out className) < 0)
            {
                return false;
            }

            var activationFactoryIid = ActivationFactoryIid;
            return RoGetActivationFactory(className, ref activationFactoryIid, out activationFactory) >= 0 &&
                activationFactory != nint.Zero;
        }
        catch (DllNotFoundException)
        {
            return false;
        }
        catch (EntryPointNotFoundException)
        {
            return false;
        }
        finally
        {
            if (activationFactory != nint.Zero) Marshal.Release(activationFactory);
            if (className != nint.Zero) WindowsDeleteString(className);
        }
    }

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int CreateForWindowDelegate(
        nint interop,
        nint hwnd,
        ref Guid iid,
        out nint captureItem);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int CreateFramePoolDelegate(nint statics, nint device, int pixelFormat, int buffers, SizeInt32 size, out nint framePool);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int CreateCaptureSessionDelegate(nint framePool, nint item, out nint captureSession);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int StartCaptureDelegate(nint captureSession);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int TryGetNextFrameDelegate(nint framePool, out nint frame);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int GetSurfaceDelegate(nint frame, out nint surface);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int GetContentSizeDelegate(nint frame, out SizeInt32 size);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int GetInterfaceDelegate(nint thisPtr, ref Guid riid, out nint p);

    [StructLayout(LayoutKind.Sequential)]
    private readonly struct SizeInt32(int width, int height)
    {
        public readonly int Width = width;
        public readonly int Height = height;
    }

    [DllImport("combase.dll", CharSet = CharSet.Unicode)]
    private static extern int WindowsCreateString(
        string sourceString,
        uint length,
        out nint hstring);

    [DllImport("combase.dll")]
    private static extern int WindowsDeleteString(nint hstring);

    [DllImport("combase.dll")]
    private static extern int RoGetActivationFactory(
        nint activatableClassId,
        ref Guid iid,
        out nint factory);

    [DllImport("d3d11.dll")]
    private static extern int CreateDirect3D11DeviceFromDXGIDevice(nint dxgiDevice, out nint direct3DDevice);
}