# PowerShell automation

Scripts in this directory provision WSL and manage the optional per-user
autostart task. Run them from an elevated PowerShell only when their help text
requires it.

`Get-WindowsStartMenuCatalog.ps1` scans the per-machine and current-user
Start Menu shortcut trees and emits a host-owned JSON catalog. The catalog
contains stable IDs and display metadata for KDE; the Windows bridge retains
the `source` and `target` fields for launch policy and must not pass them to
untrusted desktop code.

`Start-WindowsCatalogApplication.ps1` is the host-side launch adapter. KDE
entries pass only an application ID; this adapter resolves the target from the
host catalog and starts it on Windows.

Run `Sync-WindowsAppsToKde.ps1 -DistroName Ubuntu` to regenerate the catalog,
copy the bridge files into the Ubuntu user profile, generate Windows KDE
entries, refresh KDE's application cache, and update Dolphin's normal Places
entries for available Windows drives mounted by WSL, such as `C:` at `/mnt/c`.
