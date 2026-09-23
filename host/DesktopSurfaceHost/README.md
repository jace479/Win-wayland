# Desktop Surface Host

This is the first Windows-side proof for the custom bridge architecture. It
creates one borderless top-level surface for every Windows monitor, with each
surface matching that monitor's bounds.
Set `NT_PLASMA_CAPTURE_PROCESS` to a Windows process name, such as `Code`, to
enumerate its visible top-level HWNDs and show their titles on the surfaces.
The prototype mirrors each discovered window with DWM and forwards surface
mouse movement and left-click coordinates to its assigned HWND. This is an
input proof only; keyboard, full pointer state, and window reparenting are
still deferred.
At startup it performs a bounded Ubuntu WSL connectivity probe and displays the
result on each surface. This validates host-to-WSL lifecycle ownership; it does
not yet embed WSLg pixels into the surfaces.
It also listens on port `49173` for the synthetic frame protocol used by

For a firewall-free host-to-WSL test, set
`NT_PLASMA_WSL_FRAME_COMMAND` to `-d Ubuntu -- python3
/mnt/c/path/to/wsl/send-surface-frame.py --stdio` before launching. The host
reads the WSL producer's stdout and paints the matching monitor surface.
`wsl/send-surface-frame.py`; the WSL sender uses its Windows host gateway and a
received frame recolors its target monitor surface. This is the first transport
proof, not KDE pixel embedding. The prototype should be firewall-restricted to
the local WSL network.
It does not replace Explorer, capture native application windows, or embed KDE
yet.

Build and run from Windows with:

```powershell
dotnet run --project host/DesktopSurfaceHost/DesktopSurfaceHost.csproj
```

Close any surface with `Alt+F4` or from the process manager; all monitor
surfaces close together because they belong to one host process. The next slice
will replace the status surface with a controlled compositor connection and a
recovery path before any shell replacement is attempted.

The next capture adapter is specified in
`docs/architecture/windows-graphics-capture.md`. It will replace the
synthetic frame producer with Windows Graphics Capture for one allow-listed
HWND, using BGRA readback first and shared Direct3D textures later.

## HWND lifecycle preview

Run the host with a process filter to observe one application's native window
lifecycle without changing the Windows shell:

```powershell
$env:NT_PLASMA_CAPTURE_PROCESS = "Code"
dotnet run --project host/DesktopSurfaceHost/DesktopSurfaceHost.csproj
```

The watcher records `window.created`, `window.updated`, `window.focused`, and
`window.destroyed` events in `%TEMP%/nt-plasma-window-events.log`. This is
shell-preview mode only. Explorer remains active until the shell lifecycle
gates in `docs/architecture/ntkde-shell-lifecycle.md` pass, including native
window capture, KDE presentation, input routing, recovery, and rollback.

The guarded shell-preview supervisor is
`powershell/Start-NtKdeShellPreview.ps1`. It keeps Explorer running by default,
starts the host, and restores Explorer if the host exits. `-StopExplorer` is
reserved for a disposable test account after the shell-mode gates pass.