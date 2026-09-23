# Phase 1.1 Roadmap: Reliable Hybrid Integration

Phase 1.1 improves the WSLg proof of concept without replacing the Windows
shell. It is a deliberate bridge toward the long-term KDE-first desktop goal.

## Deliverables

1. Make the Plasma launcher and per-user startup task reliable and observable.
2. Validate Linux GUI windows, Windows application launchers, clipboard, audio,
   notifications, and shared file access.
3. Record exact Windows, WSL, Ubuntu, WSLg, and KDE versions during testing.
4. Define recovery behavior when Plasma fails, including a documented rollback.
5. Identify which display and window-management requirements cannot be met by
   WSLg alone.

## Boundary

Phase 1.1 keeps Winlogon, DWM, Explorer, and native Windows applications in
place. Plasma may run alongside Windows, but WSLg does not provide a single
full-screen KDE desktop surface or make KDE the Windows shell.

## Exit criteria

The phase is complete when startup can be repeated reliably, integration tests
pass on a clean test account, failures produce useful logs, and the remaining
gaps are mapped to the next display architecture.

## Next architecture decision

Before attempting Server Core as the primary host, compare a dedicated Linux
VM, a remote desktop session, and a custom compositor bridge. The selected
option must present KDE as the primary desktop while preserving Windows
authentication, native process execution, and a reliable recovery path.