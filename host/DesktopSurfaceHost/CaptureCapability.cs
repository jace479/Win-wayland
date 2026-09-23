namespace NtPlasma.DesktopSurfaceHost;

internal sealed record CaptureCapabilityResult(
    bool HwndValid,
    bool GraphicsCaptureSupported,
    bool D3D11DeviceCreated,
    bool FramePoolCreated,
    bool SharedTextureTransport,
    bool BgraReadbackTransport)
{
    public bool CanCapture =>
        HwndValid &&
        GraphicsCaptureSupported &&
        D3D11DeviceCreated &&
        FramePoolCreated &&
        (SharedTextureTransport || BgraReadbackTransport);
}