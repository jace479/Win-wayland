# Windows Graphics Capture Adapter

This is the preferred host-side path for moving native Windows application
surfaces into ntKDE. It captures a selected HWND without reparenting it or
capturing the entire Windows desktop.

## Acquisition path

1. Discover and validate the target HWND on the Windows host.
2. Create a `GraphicsCaptureItem` for that HWND using Windows Graphics
   Capture interop.
3. Create a Direct3D 11 device on the host GPU.
4. Create a `Direct3D11CaptureFramePool` for the selected pixel format.
5. Start a `GraphicsCaptureSession` and receive frame-arrived callbacks.
6. Copy or share the acquired texture into the ntKDE compositor transport.
7. Send `window.updated` metadata when bounds, title, monitor, DPI, or state
   changes.
8. Send `window.destroyed` when the source HWND closes.

## Required Windows components

- Windows Graphics Capture API (`Windows.Graphics.Capture`)
- Direct3D 11 and DXGI
- Windows Runtime interop for HWND capture-item creation
- A host GPU device, with software fallback only for diagnostics
- A compositor transport that accepts BGRA frames or shared GPU textures

The first adapter can use Windows SDK contracts plus a Direct3D interop
library. Production should avoid per-frame CPU readback when both sides can
share a GPU texture.

## Capability gates

The adapter must report a clear capability result before entering capture:

- `hwnd-valid`
- `graphics-capture-supported`
- `d3d11-device-created`
- `frame-pool-created`
- `shared-texture-transport` or `bgra-readback-transport`

If any gate fails, the host keeps the native application alive and publishes a
recoverable placeholder instead of silently dropping the surface.

## Security boundary

Capture is allow-listed by application and window policy. The Linux side never
receives an arbitrary HWND, process handle, executable path, or Windows token.
Only approved frame metadata and frame content cross the bridge.

## First implementation target

Start with one non-elevated Visual Studio Code window on one monitor and a
BGRA readback path. After frame arrival and lifecycle behavior are stable,
replace readback with shared Direct3D textures and add input forwarding.