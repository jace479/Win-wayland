# Walkthrough: Authentic Linux Desktop Shell (KDE Plasma & XFCE) on Windows via WSLg

We have pivoted Project KWin-Win from a simulated Qt mockup to an **authentic, genuine Linux desktop session** (KDE Plasma 5.27 LTS and XFCE 4.18) running from WSL2 as the primary workspace shell on Windows, operating with a strict **ZERO TCP/IP** protocol architecture.

---

## 1. What Was Built

### A. Authentic Desktop Engine (`/opt/nt-plasma/wsl/`)
- **Root Desktop Container**: Runs `Xephyr` with GLAMOR 2D hardware acceleration on host display `:0`, listening on local UNIX domain socket `/tmp/.X11-unix/X1`.
- **Dynamic Mount Fix**: Automatically handles WSLg's read-only `/tmp/.X11-unix` mount (`mount -o remount,rw` + `chmod 1777`) so nested X11 servers bind directly without TCP networking.
- **Session Selector (`start-authentic-desktop.sh`)**:
  - `plasma` (Default): Boots genuine KDE Plasma 5.27 LTS with real `plasmashell`, real `kwin_x11`, `kactivitymanagerd`, Breeze Dark panels, desktop wallpaper, and Kickoff launcher.
  - `xfce`: Boots genuine XFCE 4.18 with `xfce4-session`, `xfwm4`, `xfce4-panel`, and Whisker Menu.
  - `gnome`: Boots GNOME Flashback session.
- **Session Cleanup (`stop-authentic-desktop.sh`)**: Graceful two-phase termination (`SIGTERM` -> `SIGKILL`) of session daemons, Xephyr, and cleanup of `/tmp/.X1-lock` and `/tmp/.X11-unix/X1`.

### B. Windows Host Shell Orchestrator (`kwin_win.exe`)
- **Role**: Re-engineered to act as the native Windows Shell Orchestrator and Window Hook Manager.
- **System Tray Menu**:
  - **Desktop Environment Switcher**: Switch between KDE Plasma 5.27 LTS and XFCE 4.18 with one click.
  - **Display Target**: Switch between Primary Monitor (`1920x1080`) and Multi-Monitor Canvas Span (`6330x2160`).
  - **Presentation**: Seamless Borderless Fullscreen toggle.
  - **Lifecycle Actions**: Start / Resume Session, Restart Session, Stop Session.
  - **Quick App Launchers**: Dolphin File Manager, Konsole Terminal, KDE System Settings, KRunner.
- **Container Window Hook**: Background timer continuously monitors for the WSLg root container window (`Authentic Linux Desktop`), strips window borders (`WS_CAPTION | WS_THICKFRAME`), and anchors it to the chosen display geometry.
- **Global Hotkeys**:
  - `Alt + Space`: KRunner quick search
  - `Win + T`: KDE Konsole terminal
  - `Win + E`: KDE Dolphin file manager

### C. One-Click Windows Launchers
Located in `C:\Users\jace.zorn\.gemini\antigravity\scratch\kwin-win\`:
- [Run-KWin-Win.cmd](file:///C:/Users/jace.zorn/.gemini/antigravity/scratch/kwin-win/Run-KWin-Win.cmd): Starts the complete Windows Host Shell Orchestrator.
- [Start-Authentic-Plasma.cmd](file:///C:/Users/jace.zorn/.gemini/antigravity/scratch/kwin-win/Start-Authentic-Plasma.cmd): Starts genuine KDE Plasma 5.27 LTS directly.
- [Start-Authentic-XFCE.cmd](file:///C:/Users/jace.zorn/.gemini/antigravity/scratch/kwin-win/Start-Authentic-XFCE.cmd): Starts genuine XFCE 4.18 desktop directly.
- [Stop-Authentic-Desktop.cmd](file:///C:/Users/jace.zorn/.gemini/antigravity/scratch/kwin-win/Stop-Authentic-Desktop.cmd): Stops any active desktop session cleanly.
- Individual app launchers: `Launch-Dolphin.cmd`, `Launch-Konsole.cmd`, `Launch-System-Settings.cmd`, `Launch-KRunner.cmd`.

### D. Bidirectional Cross-OS System Cohesion
1. **Windows Apps in Linux Kickoff / Whisker Menu**:
   - Built `/opt/nt-plasma/wsl/sync-windows-apps.sh` which crawled 240 Start Menu shortcuts and generated 226 `.desktop` launchers in `~/.local/share/applications/windows-apps/`.
   - Windows apps (VS Code, Audacity, Steam, Office, etc.) appear in Kickoff/Whisker and launch directly on Windows via `wsl-open`.
2. **Unified Places & Bookmarks**:
   - Sanitized and validated `~/.local/share/user-places.xbel` for KDE Dolphin with XML validation.
   - Configured `~/.config/gtk-3.0/bookmarks` for XFCE Thunar.
   - Places directly link to Windows Home (`C:\Users\jace.zorn`), Desktop (with NTFS junction to OneDrive Desktop), Downloads, Documents, Pictures, and Videos.
3. **Cross-OS Opener (`wsl-open`)**:
   - Installed `/usr/local/bin/wsl-open` (and `/usr/local/bin/open`) to route files and URLs opened in Linux back to their default Windows host applications.

---

## 2. Verification & Test Results

### A. Zero TCP/IP Protocol Verification
Ran `ss -tulpn` in WSL2:
- **Zero X11 TCP listeners** (no port 6000, 6001, etc.).
- **Zero VNC TCP listeners** (no port 5900).
- **Zero RDP TCP listeners** (no port 3389).
- Graphical displays run strictly over `/tmp/.X11-unix/X0` and `/tmp/.X11-unix/X1` (UNIX domain sockets).
- Audio runs strictly over `/mnt/wslg/PulseServer` (PulseAudio UNIX domain socket).

### B. Live Session Tests
1. **XFCE4 Session Test**:
   - `start-authentic-desktop.sh xfce 1920 1080` spawned Xephyr and `xfce4-session`.
   - Verified active socket `/tmp/.X11-unix/X1`.
   - Verified clean shutdown via `stop-authentic-desktop.sh`.
2. **KDE Plasma 5.27 Session Test**:
   - `start-authentic-desktop.sh plasma 1920 1080` spawned Xephyr, `startplasma-x11`, `kwin_x11`, `plasmashell`, and KF5 services with GLAMOR hardware acceleration.
   - Zero crashes or assertions.
   - Verified clean shutdown and socket cleanup.
3. **Application & Bookmark Tests**:
   - Validated `user-places.xbel` with `xmllint` (exit code 0, 100% valid XML).
   - Validated `gtk3-bookmarks` in `~/.config/gtk-3.0/bookmarks`.
   - Generated 226 Windows `.desktop` application entries in `~/.local/share/applications/windows-apps/`.
4. **Host Build Test**:
   - Compiled `kwin_win.exe` with MSVC 2022 (Exit code 0).
   - Deployed Qt 6.8.2 dependencies with `windeployqt.exe`.

---

## 3. How to Launch Your Authentic Desktop

You have two easy ways to start your authentic desktop:

### Method 1: Host Orchestrator with System Tray (Recommended)
Double-click:
```
C:\Users\jace.zorn\.gemini\antigravity\scratch\kwin-win\Run-KWin-Win.cmd
```
* Automatically starts the authentic KDE Plasma desktop session.
* Hooks the window and borderless-fullscreens it on your primary monitor.
* Provides a system tray icon to switch between KDE Plasma and XFCE, change monitor targets, or launch KDE apps.

### Method 2: Direct One-Click Launchers
From PowerShell or CMD:
- **KDE Plasma**: `.\Start-Authentic-Plasma.cmd`
- **XFCE4**: `.\Start-Authentic-XFCE.cmd`
- **Multi-Monitor Canvas Spanning (All 5 Displays)**:
  `powershell.exe .\Start-Authentic-Plasma.ps1 -SpanCanvas`
- **Stop Session**: `.\Stop-Authentic-Desktop.cmd`
