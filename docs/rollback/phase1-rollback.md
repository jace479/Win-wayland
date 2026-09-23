# Phase 1 Rollback

1. Run `powershell/Unregister-PlasmaAutostartTask.ps1`.
2. Sign out or reboot; Windows returns to its normal desktop startup.
3. Stop WSL with `wsl --shutdown`.
4. Optionally remove only the test distro with
   `wsl --unregister <DistroName>`.

Do not unregister a distro containing user data without an explicit backup.
