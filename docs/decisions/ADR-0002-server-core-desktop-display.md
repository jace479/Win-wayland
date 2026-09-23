# ADR-0002: Evaluate a Dedicated Desktop Display for the Server Core Target

**Status:** Direction selected; implementation staged

## Context

The final NT-Plasma vision starts with Windows Server Core, logs the user in
through Windows, and presents KDE Plasma as the primary desktop. Native
Windows applications must remain host processes and remain usable from KDE.

WSLg is suitable for Phase 1 Linux GUI integration, but it presents individual
Linux application windows rather than a complete KDE desktop surface. It is
not sufficient by itself for the final shell experience.

## Options

### Dedicated Linux VM

Run a complete Linux guest with KDE, a real desktop session, and a controlled
display surface. Integrate Windows applications through host launchers,
shared folders, clipboard, and a window or remote-display bridge.

### Remote desktop session

Run KDE in a Linux environment and display it through RDP or a similar session
transport. This provides a complete desktop boundary but adds session latency
and complicates native Windows window integration.

### Custom compositor bridge

Build a Windows/Linux display and window-management bridge that presents KDE
as the host desktop while embedding native Windows windows. This offers the
closest final experience but has the highest implementation and recovery risk.

## Evaluation criteria

Compare the options using:

1. Full KDE desktop surface and input behavior.
2. Native Windows application window support.
3. Windows authentication and Server Core compatibility.
4. Clipboard, files, audio, notifications, and graphics performance.
5. Startup reliability, failure recovery, and rollback.
6. Security boundary and operational complexity.

## Decision direction

Investigate a custom compositor and shell bridge as the target architecture.
Existing Explorer replacement projects may provide useful shell lifecycle and
Winlogon integration patterns, but they do not by themselves embed native
Windows windows into a KDE-managed desktop. That window and display boundary
is the central NT-Plasma engineering problem.

Implementation is now staged around a custom Wayland compositor bridge. Ubuntu
under WSL2 remains the Linux runtime, while WSLg is treated as an outer
transport during experimentation rather than the final desktop owner. The
dedicated VM and remote desktop options remain fallback designs if the custom
bridge cannot meet the criteria.

## Consequences

The WSLg prototype remains useful for integration tests, but its behavior must
not be treated as evidence that it can provide the final KDE-first desktop.
The next design task is to specify the bridge components and test their
boundaries on a disposable environment.