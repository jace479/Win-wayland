# Implementation Plan: Authentic Linux Desktop Shell (KDE Plasma / XFCE / GNOME) as Primary Workspace

## Executive Summary
The user has clarified that `kwin_win.exe` should not be a simulated Qt clone of the Plasma taskbar. Instead, the user space must run an **authentic, genuine Linux desktop session** (KDE Plasma, XFCE4, or GNOME) originating from WSL2, presented seamlessly on Windows as the primary user shell, with **bidirectional synchronization of files, applications, and system info** between Windows and Linux—operating under a strict **ZERO TCP/IP protocol** constraint (relying exclusively on AF_UNIX sockets, Hyper-V VSOCK, and shared memory).

---

## Architecture & Design

```
+-----------------------------------------------------------------------------------+
|                                 WINDOWS HOST                                      |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | kwin_win.exe (Host Shell Orchestrator & Multi-Monitor Window Manager)       |  |
|  |  - Tray Icon: Session switcher (Plasma / XFCE / GNOME), Display selector   |  |
|  |  - HWND Manager: Hooks WSLg container window, strips borders, anchors to    |  |
|  |    fullscreen / borderless desktop on chosen monitor(s)                     |  |
|  +-----------------------------------------------------------------------------+  |
|                                         |                                         |
|                 Hyper-V VSOCK / WSLg Local AF_UNIX Bridge                         |
|                                         v                                         |
|  +-----------------------------------------------------------------------------+  |
|  | WSL2 UBUNTU 24.04 LTS (Zero TCP/IP Network Ports)                           |  |
|  |                                                                             |  |
|  |  [WSLg System Distro Socket]                                                |  |
|  |     /tmp/.X11-unix/X0 (Host Display) & /mnt/wslg/PulseServer (Audio)        |  |
|  |                           |                                                 |  |
|  |                           v                                                 |  |
|  |  [Root Desktop Container Server: Xephyr with Glamor 2D Acceleration]        |  |
|  |     Listens on AF_UNIX socket: /tmp/.X11-unix/X1 (Mode 1777, ZERO TCP)      |  |
|  |     Maps as native hardware-accelerated top-level window to Windows host    |  |
|  |                           |                                                 |  |
|  |          +----------------+----------------+                                |  |
|  |          | (Session Selection via Switcher)|                                |  |
|  |          v                                 v                                |  |
|  |  +-----------------------+     +-----------------------+                    |  |
|  |  | Authentic KDE Plasma  |     | Authentic XFCE4 /     |                    |  |
|  |  | 5.27 LTS Desktop      |     | GNOME Flashback       |                    |  |
|  |  | - Real plasmashell    |     | - Real xfce4-panel    |                    |  |
|  |  | - Real kwin_x11       |     | - Real xfwm4 & desktop|                    |  |
|  |  | - Real Kickoff & Tray |     | - Whisker App Menu    |                    |  |
|  |  | - Real KRunner & OSD  |     |                       |                    |  |
|  |  +-----------------------+     +-----------------------+                    |  |
|  |                           |                                                 |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  | Bidirectional Cohesive System Bridge:                                 |  |  |
|  |  | 1. Windows Start Menu -> Linux .desktop app sync (Run Win apps in KDE) |  |  |
|  |  | 2. Dolphin & Thunar Places -> Windows Home, Desktop, Downloads, Docs |  |  |
|  |  | 3. wsl-open -> Opens files & URLs in default Windows applications   |  |  |
|  |  | 4. Zero TCP Audio -> PulseAudio socket to Windows speakers             |  |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## User Review Required

> [!IMPORTANT]
> **Zero TCP/IP Guarantee:** No X11 TCP listeners (`:6000`), no VNC TCP servers (`:5900`), and no RDP TCP listeners (`:3389`) will be used. All communications flow through `/tmp/.X11-unix/` AF_UNIX domain sockets and WSLg Hyper-V VSOCK.

> [!IMPORTANT]
> **Container vs. Native Rail Limitation:** As discovered, WSLg's `rdprail-shell.so` only exports standard `xdg_toplevel` application windows and ignores root/layer-shell desktop surfaces (wallpaper and panels). To run an authentic desktop session with full taskbars and wallpapers, a root container window (hardware-accelerated `Xephyr -glamor` on `:0`) is used. WSLg automatically renders this container window as a native Windows HWND, which `kwin_win.exe` or helper scripts anchor into a seamless borderless desktop.

---

## Open Questions

> [!NOTE]
> 1. **Default Monitor Preference:** You have 5 connected displays (`1920x1080`, `1680x1050`, `1680x1050`, `1920x1080`, `1050x1680`). Should the desktop session launch borderless-fullscreen on your primary monitor (`1920x1080`), or span across all displays as a single virtual canvas (`6330x2160`)? *(Recommendation: Default to the primary monitor with a tray option or parameter to select other monitors or full-canvas span).*
> 2. **Default Desktop Environment:** Should KDE Plasma 5.27 be the default desktop, with XFCE4 and GNOME available as 1-click alternatives?

---

## Proposed Changes

### Component 1: WSL Session & Authentic Desktop Engine
Location: Ubuntu 24.04 (`jace479` / `/opt/nt-plasma/wsl/`)

#### [NEW] `/opt/nt-plasma/wsl/start-authentic-desktop.sh`
- Implements the master launch sequence for the genuine desktop session.
- Configures `/tmp/.X11-unix` permissions (`chmod 1777 /mnt/wslg/.X11-unix`) so non-root users can create nested display sockets (`:1`).
- Launches `Xephyr` with GLAMOR hardware acceleration, resizeable support, custom title, and geometry matching the target monitor.
- Checks the requested session type:
  - `plasma` (default): Launches `export DISPLAY=:1; export DESKTOP_SESSION=plasma; export KDE_FULL_SESSION=true; startplasma-x11`.
  - `xfce`: Launches `export DISPLAY=:1; export DESKTOP_SESSION=xfce; xfce4-session`.
  - `gnome`: Launches `export DISPLAY=:1; gnome-session --session=gnome-flashback-metacity`.
- Traps exit signals (`SIGINT`, `SIGTERM`) to cleanly terminate the session, KWin/XFWM, and Xephyr, removing stale socket files.

#### [NEW] `/opt/nt-plasma/wsl/stop-authentic-desktop.sh`
- Gracefully terminates Xephyr, Plasma/XFCE/GNOME, `plasmashell`, `kded5`, and cleans up lock files.

#### [NEW] `/opt/nt-plasma/wsl/sync-windows-apps.sh`
- Inspects Windows Start Menu shortcuts in `/mnt/c/ProgramData/Microsoft/Windows/Start Menu/Programs` and `/mnt/c/Users/jace.zorn/AppData/Roaming/Microsoft/Windows/Start Menu/Programs`.
- Automatically generates Linux `.desktop` files in `~/.local/share/applications/windows/`.
- Allows launching Windows applications (VS Code, Chrome, Office, etc.) directly from the KDE Kickoff menu or XFCE Whisker menu using `wsl-open` / `cmd.exe /c start`.

#### [MODIFY] `~/.local/share/user-places.xbel` and `~/.config/gtk-3.0/bookmarks`
- Ensures Dolphin (KDE) and Thunar (XFCE) bookmark all Windows user directories:
  - `Windows Home` (`/mnt/c/Users/jace.zorn`)
  - `Desktop` (`/mnt/c/Users/jace.zorn/Desktop`)
  - `Downloads` (`/mnt/c/Users/jace.zorn/Downloads`)
  - `Documents` (`/mnt/c/Users/jace.zorn/Documents`)

---

### Component 2: Windows Host Shell Orchestrator (`kwin_win.exe` & Launchers)
Location: `C:\Users\jace.zorn\.gemini\antigravity\scratch\kwin-win\`

#### [MODIFY] [`src/core/main.cpp`](file:///C:/Users/jace.zorn/.gemini/antigravity/scratch/kwin-win/src/core/main.cpp)
- Repurpose `kwin_win.exe` from a mock taskbar to the **Host Shell Orchestrator & Window Manager**:
  1. Starts `wsl.exe -d Ubuntu -u jace479 /opt/nt-plasma/wsl/start-authentic-desktop.sh [session] [width] [height]`.
  2. Hooks the resulting WSLg window via Windows Win32 API (`FindWindow`, `SetWindowLongPtr`, `SetWindowPos`).
  3. Applies borderless fullscreen framing to the target monitor (removes titlebar and window border for an authentic native shell experience).
  4. Manages a System Tray icon with menu options:
     - Switch Desktop: KDE Plasma / XFCE / GNOME
     - Target Monitor: Display 1 (1920x1080), Display 2 (1680x1050), etc.
     - Toggle Borderless Fullscreen / Windowed Mode
     - Restart Desktop Session / Quit Session

#### [NEW] `Start-Authentic-Plasma.cmd` & `Start-Authentic-Plasma.ps1`
- Direct one-click Windows launcher for KDE Plasma without needing any build steps.

#### [NEW] `Start-Authentic-XFCE.cmd` & `Start-Authentic-XFCE.ps1`
- Direct one-click Windows launcher for XFCE4 desktop.

#### [NEW] `Stop-Authentic-Desktop.cmd` & `Stop-Authentic-Desktop.ps1`
- Clean shutdown utility for all running desktop sessions.

---

### Component 3: Package Installation in WSL
- Install `xfce4` and `xfce4-session` in Ubuntu WSL2:
  `sudo apt-get update && sudo apt-get install -y xfce4 xfce4-goodies xfce4-terminal`

---

## Verification Plan

### Automated Tests
1. **Zero TCP/IP Socket Verification:**
   - Execute `ss -tulpn` in WSL2 before and after starting the desktop session.
   - Confirm ZERO listening TCP ports on `6000`, `5900`, `3389`, or any other graphical port.
   - Confirm display socket exists exclusively as `/tmp/.X11-unix/X1` (UNIX domain socket).
2. **Process Health Check:**
   - Verify `Xephyr`, `plasmashell`, `kwin_x11`, `kded5` (or `xfce4-session`, `xfwm4`, `xfce4-panel`) are running with valid PIDs.
3. **Build Verification:**
   - Compile `kwin_win.exe` with MSVC 2022 to confirm zero compilation or link errors.

### Manual / Visual Verification
1. **Authentic KDE Plasma Verification:**
   - Run `Start-Authentic-Plasma.cmd`.
   - Confirm genuine KDE Plasma 5.27 desktop appears with real Plasma Breeze wallpaper, real Breeze taskbar, Kickoff launcher, and system tray.
   - Click Kickoff -> Verify authentic KDE categories, Plasma widgets, and real window decorations.
2. **Windows <-> WSL Cohesion:**
   - Open Dolphin -> Verify Windows folders (`Windows Home`, `Desktop`, `Downloads`) are in Places.
   - Open Kickoff -> Navigate to "Windows Applications" -> Launch a Windows app to verify cross-OS execution.
3. **Desktop Switching:**
   - Run `Start-Authentic-XFCE.cmd` -> Confirm XFCE 4.18 desktop loads with Whisker menu and Thunar.
