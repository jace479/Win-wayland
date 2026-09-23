# Ubuntu automation

Run provisioning scripts inside the target Ubuntu WSL2 distro. Scripts should
be idempotent and must not install or enable a Linux display manager.

`launch-windows-app.sh` is the ID-only KDE launcher for Windows catalog
entries. Set `NT_PLASMA_WINDOWS_CATALOG` to the synchronized Windows catalog
path when installing the generated `.desktop` files. Entries are installed
directly in the standard `~/.local/share/applications` directory so KDE treats
them as applications. The script forwards only the stable application ID to
the Windows PowerShell adapter.

`plasma-launch.sh` selects Wayland only when a KWin DRM render node is
available. Under WSLg it records the missing DRM capability and uses the
working X11 session instead of allowing Plasma Wayland to start and then drop.

While the host surface prototype is running, test the first WSL-to-host visual
transport with `python3 wsl/send-surface-frame.py 1 1920 1080 32 96 160`.

`capture-x11-frame.py` captures actual pixels from the WSLg X11 root display
through `libX11` and emits the same binary frame format. Example:
`python3 wsl/capture-x11-frame.py --monitor 1 --x 0 --y 0 --width 1920
--height 1080`.

`weston-bridge.sh` is the nested compositor entry point for the custom bridge.
It uses WSLg's X11 display as the outer transport, creates a dedicated
Wayland socket, and can attach `plasmashell` with
`NT_PLASMA_START_PLASMASHELL=1`. It requires the Ubuntu `weston` package and
is experimental until monitor, input, and recovery tests pass.
