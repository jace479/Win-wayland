# Native Windows Window Composition

This document defines how native Windows application windows eventually become
first-class surfaces in the KDE desktop. Launching an application is already
working; composition is a separate bridge capability.

## Target model

```text
Windows application
    -> host window adapter
    -> native surface stream and window metadata
    -> compositor bridge
    -> KDE desktop surface
```

Explorer replacement is not the capture mechanism. It only changes which
desktop shell presents the user experience. Native Windows applications remain
Win32/DWM windows and must be surfaced through this composition bridge whether
Explorer is active or not.

## Unified visual surface

There must be no apparent boundary between Windows and Linux applications.
KDE owns the visible presentation for both origins:

- identical KDE title-bar and decoration behavior
- identical task-manager and focus behavior
- identical placement, snapping, resizing, and monitor handling
- identical icon, title, menu, and notification treatment
- no visible native Windows non-client frame around captured content

Every application is a first-class KDE citizen regardless of source. The
shared surface contract covers the complete visible and interactive lifecycle:

- discovery and stable identity
- launcher and application-menu entry
- icon and title presentation
- decoration and task-manager entry
- focus, keyboard, pointer, and accessibility behavior
- placement, snapping, resizing, minimizing, and maximizing
- notifications, clipboard, files, and shutdown
- failure reporting and recovery

The source may be Win32, WSL, APT, Flatpak, MSIX, or another approved runtime,
but source-specific details remain behind the bridge adapters.

Windows keeps ownership of the native process and client surface, but the
bridge captures the client area and presents it inside a KDE foreign surface.
The host must not expose the original HWND frame as the user-facing window.

KDE owns the desktop presentation model. Windows remains the owner of the
native process, security boundary, and underlying Win32 window. The bridge
must not duplicate the application process or ask Linux to execute the
Windows target directly.

## Window identity

Every integrated window needs a host-issued identifier that is distinct from
the process ID and HWND. The identifier must remain stable across metadata
updates but be invalidated when the host window is destroyed. The host reports:

- application ID from the allow-listed catalog
- window ID and lifecycle state
- title and role
- bounds and monitor
- DPI scale and device-pixel size
- minimized, maximized, fullscreen, and modal state
- focus and activation state
- whether the window is eligible for integration

## Surface transport candidates

The first real implementation should compare:

1. Windows Graphics Capture, with frames copied into a host compositor texture.
2. Desktop Duplication, where full-screen or monitor capture is appropriate.
3. A redirected HWND surface using a composition-aware Windows API.

The bridge should prefer per-window capture. Capturing the whole Windows
desktop would include Explorer and unrelated applications and would prevent
KDE from managing windows independently.

## Preferred efficient path

Use Windows Graphics Capture on the host and Direct3D textures for frames:

1. Resolve the selected HWND from the host-owned window ID.
2. Create a `GraphicsCaptureItem` for that HWND.
3. Capture frames into a host Direct3D device.
4. Reuse a small texture pool instead of allocating per frame.
5. Share or copy the frame into the compositor bridge format.
6. Send metadata and frame sequence separately from pixel data.

The bridge should prefer GPU texture sharing when both sides support the same
device boundary. Otherwise it should use bounded BGRA readback with frame
dropping under load. The compositor must always prefer the newest frame rather
than queueing stale frames.

## HWND composition options

There are three different meanings of "HWND composition":

- **DWM thumbnail:** efficient for a preview, but not a true interactive child
  window and not suitable as the final KDE surface.
- **Windows Graphics Capture:** the preferred final approach for per-window
  pixels, with input routed back to the source HWND.
- **Reparenting or child-window embedding:** fragile across DWM, DPI, elevated
  processes, and different desktop sessions; do not use as the primary design.

The final bridge should therefore compose captured HWND surfaces rather than
reparent arbitrary native windows. The host keeps HWND ownership and KDE owns
the presentation surface.

The no-boundary requirement is met only when the captured frame excludes the
Windows non-client area and KDE supplies the complete visible decoration. A
temporary DWM thumbnail with its original frame is useful for diagnostics but
does not satisfy this requirement.

## Input and focus

KDE sends pointer, keyboard, focus, resize, and close requests using the host
window ID. The Windows adapter validates ownership and translates those
requests into the native window input model. Focus changes must be acknowledged
by the host so KDE does not display stale active-window state.

## Composition rules

- Windows frames are presented inside KDE-managed surface bounds.
- Native dialogs and menus retain their parent/owner relationship.
- Occlusion and minimized windows stop or reduce frame capture.
- Monitor changes trigger a new bounds and DPI negotiation.
- Secure desktop, elevated prompts, protected content, and unrelated windows
  are not captured without an explicit policy.
- If capture fails, KDE keeps a recoverable placeholder and the Windows app
  remains alive on the host.

## First vertical slice

1. Launch one allow-listed Windows test application.
2. Discover its top-level HWND and issue a host window ID.
3. Capture that one window into a host-owned Direct3D texture.
4. Display the texture in one host monitor surface.
5. Forward focus, resize, and close for that window.
6. Test destruction, minimization, DPI change, and capture failure recovery.

The acceptance test must include a Windows app beside a Linux app and verify
that an observer cannot identify the origin from frame, title bar, task entry,
focus indication, or resize behavior alone.

This slice deliberately excludes shell replacement, arbitrary HWND capture,
protected content, and multi-window application suites.

The same slice is suitable for shell-preview mode while Explorer remains
active. It proves how a selected native window is viewed and controlled from
the KDE desktop before any shell transition is attempted.

The current prototype implements the Linux-side foreign-surface state and
pointer-event contract in `integration/foreign_surface.py`. The next bridge
boundary is a real Wayland client or compositor protocol that presents this
state inside KDE.

The initial protocol draft is
`nt-plasma-foreign-surface-v1.xml`. It defines host-window identity, metadata,
buffer attachment, configure/focus/close events, and rejected-frame reporting.
The compositor implementation must enforce increasing frame sequences and
bounded surface dimensions before presenting a buffer.

The compositor-neutral registry in `integration/desktop_surface_registry.py`
is the next adapter layer. It presents each Windows window independently to
KDE with its own application identity, live title, icon, monitor, geometry, and
frame state, while routing pointer events by stable surface ID.

The host event factory in `integration/surface_events.py` supplies the typed
`window.created`, `window.updated`, and `window.destroyed` messages that feed
this registry. It keeps the host HWND and executable path private to the
Windows side.

The compositor-facing adapter in `integration/wayland_surface_adapter.py`
maps those registry records to named Wayland foreign-surface roles. It is
compositor-neutral today. The in-process endpoint in
`integration/wayland_foreign_surface_protocol.py` now exercises the protocol
requests and events, including ordered frame attachment and rejection. This
is a testable contract boundary, not a native Wayland implementation: the
next implementation binds these operations to generated protocol bindings in
a KWin/Weston client or plugin.

Generated Windows application entries use normal KDE categories and application
semantics. Their Windows origin remains internal bridge metadata rather than a
visible `Windows` menu category, so KDE presents them alongside Linux programs.