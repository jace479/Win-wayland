using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

internal sealed class D3D11On12DeviceBridge : IDisposable
{
    private const int CreateWrappedResourceVtableIndex = 43;
    private const uint D3D12ResourceStateCommon = 0;
    private const uint D3D12ResourceStatePixelShaderResource = 0x40;
    private static readonly Guid DeviceIid = new("189819F1-1DB6-4B57-BE54-1821339B85F7");
    private static readonly Guid QueueIid = new("0EC870A6-5D7E-4C22-8CFC-5BAAE07616ED");
    private static readonly Guid D3D11On12DeviceIid = new("85611E73-70A9-490E-9614-A9E302777904");
    private static readonly Guid D3D11ResourceIid = new("DC8E63F3-D12B-4952-B47B-5E45026A862D");
    private nint d3d12Device;
    private nint commandQueue;
    private nint d3d11Device;
    private nint d3d11Context;
    private nint d3d11On12Device;

    private D3D11On12DeviceBridge(nint d3d12Device, nint commandQueue, nint d3d11Device, nint d3d11Context, nint d3d11On12Device)
    {
        this.d3d12Device = d3d12Device;
        this.commandQueue = commandQueue;
        this.d3d11Device = d3d11Device;
        this.d3d11Context = d3d11Context;
        this.d3d11On12Device = d3d11On12Device;
    }

    public static bool TryCreate(out D3D11On12DeviceBridge? bridge)
    {
        bridge = null;
        nint d3d12Device = nint.Zero;
        nint commandQueue = nint.Zero;
        nint d3d11Device = nint.Zero;
        nint d3d11Context = nint.Zero;
        nint d3d11On12Device = nint.Zero;
        nint queueArray = nint.Zero;
        try
        {
            var deviceIid = DeviceIid;
            if (D3D12CreateDevice(nint.Zero, 0xB000, ref deviceIid, out d3d12Device) < 0)
            {
                return false;
            }

            var queueDescription = new CommandQueueDescription();
            var queueIid = QueueIid;
            var vtable = Marshal.ReadIntPtr(d3d12Device);
            var createQueue = Marshal.GetDelegateForFunctionPointer<CreateCommandQueueDelegate>(
                Marshal.ReadIntPtr(vtable, IntPtr.Size * 8));
            if (createQueue(d3d12Device, ref queueDescription, ref queueIid, out commandQueue) < 0)
            {
                return false;
            }

            queueArray = Marshal.AllocHGlobal(IntPtr.Size);
            Marshal.WriteIntPtr(queueArray, commandQueue);
            var result = D3D11On12CreateDevice(
                d3d12Device,
                0,
                nint.Zero,
                0,
                queueArray,
                1,
                0,
                out d3d11Device,
                out d3d11Context,
                out _);
            if (result < 0 || d3d11Device == nint.Zero || d3d11Context == nint.Zero)
            {
                return false;
            }

            var d3d11On12DeviceIid = D3D11On12DeviceIid;
            if (Marshal.QueryInterface(d3d11Device, ref d3d11On12DeviceIid, out d3d11On12Device) != 0)
            {
                return false;
            }

            bridge = new D3D11On12DeviceBridge(d3d12Device, commandQueue, d3d11Device, d3d11Context, d3d11On12Device);
            d3d12Device = commandQueue = d3d11Device = d3d11Context = d3d11On12Device = nint.Zero;
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
        finally
        {
            if (queueArray != nint.Zero) Marshal.FreeHGlobal(queueArray);
            Release(d3d11Context);
            Release(d3d11Device);
            Release(d3d11On12Device);
            Release(commandQueue);
            Release(d3d12Device);
        }
    }

    public bool TryCreateWrappedResource(
        nint d3d12Resource,
        uint bindFlags,
        uint miscFlags,
        uint inState,
        uint outState,
        out nint d3d11Resource)
    {
        d3d11Resource = nint.Zero;
        if (d3d12Resource == nint.Zero || d3d11On12Device == nint.Zero)
        {
            return false;
        }

        var flags = new D3D11ResourceFlags
        {
            BindFlags = bindFlags,
            MiscFlags = miscFlags,
            CPUAccessFlags = 0,
            StructureByteStride = 0,
        };
        var resourceIid = D3D11ResourceIid;
        var vtable = Marshal.ReadIntPtr(d3d11On12Device);
        var createWrappedResource = Marshal.GetDelegateForFunctionPointer<CreateWrappedResourceDelegate>(
            Marshal.ReadIntPtr(vtable, IntPtr.Size * CreateWrappedResourceVtableIndex));
        var result = createWrappedResource(
            d3d11On12Device,
            d3d12Resource,
            ref flags,
            inState,
            outState,
            ref resourceIid,
            out d3d11Resource);
        if (result < 0 || d3d11Resource == nint.Zero)
        {
            Release(d3d11Resource);
            d3d11Resource = nint.Zero;
            return false;
        }

        return true;
    }

    public void Dispose()
    {
        Release(d3d11Context);
        Release(d3d11Device);
        Release(d3d11On12Device);
        Release(commandQueue);
        Release(d3d12Device);
        d3d11Context = d3d11Device = d3d11On12Device = commandQueue = d3d12Device = nint.Zero;
        GC.SuppressFinalize(this);
    }

    private static void Release(nint value)
    {
        if (value != nint.Zero) Marshal.Release(value);
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct CommandQueueDescription
    {
        public uint Type;
        public int Priority;
        public uint Flags;
        public uint NodeMask;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct D3D11ResourceFlags
    {
        public uint BindFlags;
        public uint MiscFlags;
        public uint CPUAccessFlags;
        public uint StructureByteStride;
    }

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int CreateWrappedResourceDelegate(
        nint d3d11On12Device,
        nint d3d12Resource,
        ref D3D11ResourceFlags flags,
        uint inState,
        uint outState,
        ref Guid riid,
        out nint d3d11Resource);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate int CreateCommandQueueDelegate(
        nint device,
        ref CommandQueueDescription description,
        ref Guid riid,
        out nint commandQueue);

    [DllImport("d3d12.dll")]
    private static extern int D3D12CreateDevice(
        nint adapter,
        uint minimumFeatureLevel,
        ref Guid riid,
        out nint device);

    [DllImport("d3d11.dll")]
    private static extern int D3D11On12CreateDevice(
        nint device,
        uint flags,
        nint featureLevels,
        uint featureLevelsCount,
        nint commandQueues,
        uint numQueues,
        uint nodeMask,
        out nint d3d11Device,
        out nint immediateContext,
        out uint chosenFeatureLevel);
}