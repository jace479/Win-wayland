# ntKDE Shell Lifecycle

ntKDE eventually replaces Explorer as the user-facing Windows shell while
leaving Winlogon, DWM, security, drivers, and native Windows processes under
Windows control. Shell replacement is a late-stage capability, not a Phase 1
startup shortcut.

## Session states

```text
WindowsAuthenticated
    -> HostBridgeStarting
    -> LinuxRuntimeStarting
    -> CompositorStarting
    -> DesktopReady
    -> Recovering
    -> WindowsRecoveryShell
```

The host must persist the current state and a reason for every transition.
The recovery state must be reachable from any state after authentication.

The prototype state machine is implemented in
`integration/shell_lifecycle.py`. It deliberately models shell mode without
changing the current Windows shell.

Every transition is recorded with source state, target state, reason, and a
UTC timestamp. This history is the minimum diagnostic record required for
recovery decisions and later startup logs.

The controller exposes a JSON-safe snapshot containing the current state,
failure reason, and transition history. A host implementation can persist this
snapshot without serializing process handles or credentials.

## Shell capability contract

The final ntKDE shell must cover the capabilities users normally receive from
Explorer and the surrounding Windows shell, while presenting them through KDE:

- Desktop surface, wallpaper, widgets, panels, and system tray
- Application launcher, search, settings, notifications, and session actions
- Task management for visible windows and sanitized Windows/Linux processes
- Focus, switching, minimize, maximize, snap, workspaces, and accessibility
- Dolphin file workflows and normal Windows drive Places
- Clipboard, files, audio, notifications, and recovery controls

The Windows host remains authoritative for process identity, permissions,
security-sensitive actions, and native window ownership. The Linux bridge
publishes sanitized snapshots and typed actions. Protected or session-0
processes may be visible as metadata but must reject unauthorized control
requests.

## Startup contract

1. Windows authenticates the user normally.
2. The host bridge starts under the user session.
3. The bridge verifies its configuration and IPC policy.
4. Ubuntu/WSL starts as the Linux runtime.
5. The selected compositor surface starts and reports readiness.
6. KDE reports that the desktop is usable.
7. Only after readiness is proven may ntKDE enter shell mode.

During development, Explorer remains the Windows shell until shell-preview
gates pass. In the final build, Explorer is not required: ntKDE's supervisor,
compositor, desktop session, and recovery UI own the complete user-facing
desktop lifecycle.

## Windows application visibility

Replacing Explorer changes the shell, not the Windows windowing system. Native
applications continue to create Win32 top-level windows and DWM continues to
own their underlying composition. ntKDE must provide the visible desktop
surface for those windows through the native-window composition bridge:

```text
Native Windows application
    -> Win32 HWND and DWM surface
    -> Windows capture adapter
    -> ntKDE compositor surface
    -> KDE desktop, panels, and task manager
```

The Windows application remains a host process. KDE displays its captured
surface and sends focus, pointer, keyboard, resize, and close requests back to
the owning HWND. If capture fails, the host recovery path must remain usable.

This can be developed now as shell-preview mode: ntKDE owns borderless monitor
surfaces and composes selected native windows while Explorer remains active
underneath. Shell-preview mode must never modify the Winlogon shell value or
terminate Explorer automatically. Its Explorer restart behavior is only a
temporary development fallback, not a final runtime dependency.

## Recovery contract

- A compositor failure must not terminate native Windows applications.
- A KDE failure must not terminate the host bridge.
- A bridge timeout must return control to a usable Windows shell.
- The recovery path must work without KDE, WSL, or network access.
- Every failed startup must leave a diagnostic reason and timestamp.

The first recovery implementation should offer a host-side hotkey or tray
action that closes ntKDE surfaces and restores Explorer visibility. A later
Server Core implementation can use a dedicated recovery process instead of
Explorer, but it must retain an equivalent safe path.

## Shell-mode gates

Do not replace Explorer until all of these are demonstrated on a disposable
test account:

1. KDE desktop surface starts repeatedly after logon.
2. Windows and Linux application launch works from KDE.
3. Native Windows windows can be composed and focused in KDE.
4. Keyboard, pointer, DPI, clipboard, files, audio, and notifications work.
5. Host and Linux bridge failures recover without rebooting.
6. The emergency Windows recovery path has been exercised repeatedly.

## Current position

The WSLg prototype validates application integration and bridge contracts. The
custom compositor bridge and host surface prototypes are the path toward shell
mode. Explorer replacement remains disabled until the shell-mode gates pass.