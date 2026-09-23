# Custom Bridge Target Architecture

This document describes the selected investigation path for the final
Server Core vision. It is design work plus staged prototypes. The final
ntKDE desktop does not depend on Explorer; Explorer is retained only as a
temporary development fallback and recovery option.

## Responsibilities

### Windows host bridge

- Starts after Windows authentication through a recoverable shell lifecycle.
- Launches and monitors native Windows applications.
- Tracks native top-level windows, focus, input, DPI, and monitor changes.
- Provides a controlled IPC endpoint to the Linux session.
- Starts an independent ntKDE recovery path if the Linux desktop fails.
- May launch Explorer only as a development fallback while shell-preview mode
   is being validated.

The first host-side prototype is a policy-enforcing broker. It accepts only
typed request messages from a ready, authenticated session, resolves Windows
applications through an allow-list, and requires a separate capability for
privileged operations. It does not execute arbitrary shell commands.

The first display-side proof is `host/DesktopSurfaceHost`. It creates one
borderless surface per Windows monitor while leaving Explorer and native
application ownership unchanged. These surfaces are only a host boundary test;
they are not yet a compositor or a window-embedding solution.

### Wayland compositor bridge

- Owns the desktop surface presented to Windows for each monitor.
- Accepts Linux desktop content through a controlled Wayland-compatible
   protocol boundary.
- Composes KDE surfaces and native Windows application surfaces into one
   desktop model.
- Routes input, focus, scaling, monitor changes, and shutdown events.
- Keeps WSLg as an experimental outer transport until the host surface path is
   proven.

### Linux desktop bridge

- Starts the KDE Plasma session and presents the primary desktop surface.
- Publishes Linux application windows and desktop actions to the host bridge.
- Requests Windows application launches through explicit identifiers.
- Coordinates focus, clipboard, files, audio, notifications, and shutdown.

### Display and window boundary

The bridge must define how a native Win32 window is represented in the KDE
desktop. Candidate mechanisms include redirected surfaces, host-owned child
windows, or a compositor protocol. The design must account for input capture,
occlusion, resizing, multi-monitor layouts, high-DPI scaling, menus, dialogs,
and accessibility.

## Explorer replacement relationship

Explorer replacement is not a runtime dependency of ntKDE. Existing Explorer
replacement projects may provide useful lifecycle ideas, but the final ntKDE
supervisor, compositor bridge, desktop session, and recovery path must work
without Explorer running. The host bridge, Linux desktop session, and
native-window transport remain separate responsibilities.

## Design gates

1. Prove a native Windows test window can be displayed and focused by the KDE
   session without replacing the production shell.
2. Prove crash recovery returns to a usable Windows shell.
3. Prove the bridge works with a minimal Server Core installation.
4. Define a signed, authenticated IPC boundary before supporting arbitrary
   application launches.
5. Test one monitor, multiple monitors, DPI changes, clipboard, and shutdown.

## Staged implementation

1. Create one host surface per monitor and report exact bounds.
2. Establish a compositor control channel with authenticated lifecycle events.
3. Render a synthetic Wayland test surface inside one host monitor surface.
4. Render a minimal Linux client surface through the same path.
5. Attach Plasma only after surface lifetime, input, and recovery pass.
6. Add native Windows window capture and composition after Linux rendering is
   stable.

Native Windows surface behavior is specified separately in
`native-window-composition.md`. Application launching and native-window
composition are separate capabilities: a successful launch does not imply that
the window can safely be captured, focused, resized, or embedded.

No shell replacement should be attempted until these gates have a disposable
test environment, an emergency recovery path, and a documented rollback.