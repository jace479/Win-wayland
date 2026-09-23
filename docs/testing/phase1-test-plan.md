# Phase 1 Test Plan

## Acceptance criteria

1. Windows 11 remains the host OS.
2. Ubuntu WSL2 starts automatically after Windows logon.
3. KDE Plasma starts automatically through WSLg.
4. A Windows application starts from a KDE launcher entry.
5. A Linux application starts from KDE.
6. Representative daily tasks complete without opening Explorer.

## Test sequence

1. Verify `wsl --status`, `wsl --version`, and `wsl -l -v`.
2. Run the Ubuntu provisioning scripts and restart WSL.
3. Launch a smoke-test GUI application before attempting Plasma.
4. Run `wsl/plasma-launch.sh` manually and inspect its log.
5. Register the per-user Scheduled Task, sign out, and sign in again.
6. Launch Notepad (Windows) and Kate or Dolphin (Linux) from KDE.
7. Complete file open/save, copy/paste, window management, and notification
   tasks using KDE, without opening Explorer.

Repeat the logon test three times and record failures, startup duration, and
the exact Windows/Ubuntu/Plasma versions.
