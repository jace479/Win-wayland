# Project NT-Plasma / NT-KDE

This directory contains the complete codebase, configurations, launchers, and integration assets for running an **authentic Linux Desktop Session (KDE Plasma 5.27 LTS / XFCE 4.18)** hosted inside Ubuntu 24.04 WSL2 and presented seamlessly to Windows 11.

---

## Architecture & Design Principles
1. **STRICTLY ZERO TCP/IP Ports:**
   - No X11 TCP port 6000.
   - No VNC port 5900.
   - No RDP port 3389.
   - All display, graphics, audio, and shell IPC communication runs exclusively over **local AF_UNIX domain sockets** (`/mnt/wslg/runtime-dir/wayland-0`, `/mnt/wslg/PulseServer`, `/tmp/.X11-unix/X0` and `X1`) and **Hyper-V VSOCK**.

2. **Native Wayland Presentation (WSLg):**
   - Direct support for `WAYLAND_DISPLAY=wayland-0` and nested Wayland compositors (`kwin_wayland`).
   - WSLg discovers and maps all physical displays (including portrait and mixed-resolution 5-monitor setups).

3. **No Invasive Windows Frame Hooking:**
   - Native Windows host windows (Explorer, SCCM, Edge, VS Code, etc.) retain 100% untouched Win32 styles (`WS_CAPTION`, `WS_THICKFRAME`).
   - Host orchestrator acts solely as a session manager, global hotkey handler, and system tray controller.

---

## Directory Structure

```
nt-plasma/
├── windows-host/
│   ├── src/                    # C++ source for Qt 6 host orchestrator & tray
│   │   ├── core/main.cpp       # Main entry, global hotkeys (Alt+Space, Win+E, Win+T), tray
│   │   ├── tray/               # System tray bridge and menu actions
│   │   ├── ui/                 # Models and window abstractions
│   │   └── uwp/                # UWP package discovery
│   ├── qml/                    # QML interfaces and Breeze desktop styling
│   ├── icons/                  # High-resolution Breeze & Plasma application icons
│   ├── CMakeLists.txt          # CMake project configuration (MSVC 2022 + Qt 6)
│   ├── build/Release/          # Compiled kwin_win.exe and Qt 6 runtime binaries
│   ├── Run-KWin-Win.cmd        # One-click launcher for the host orchestrator tray
│   └── scripts/                # Windows cmd/ps1 scripts to launch individual KDE apps or sessions
│       ├── Start-Authentic-Plasma.cmd / .ps1
│       ├── Start-Authentic-XFCE.cmd / .ps1
│       ├── Launch-Dolphin.cmd / .ps1
│       ├── Launch-Konsole.cmd / .ps1
│       ├── Launch-KRunner.cmd / .ps1
│       ├── Launch-System-Settings.cmd / .ps1
│       └── Stop-Authentic-Desktop.cmd / .ps1
│
├── wsl-desktop/                # Linux bash scripts (located in /opt/nt-plasma/wsl in WSL)
│   ├── start-authentic-desktop.sh  # Unified session launcher (plasma / xfce, multi-resolution)
│   ├── stop-authentic-desktop.sh   # Clean session killer and lockfile cleaner
│   ├── launch-app.sh               # Standalone Wayland app launcher
│   ├── ensure-wslg-patch.sh        # WSLg Weston rail-shell stabilization
│   └── patched-rdp-backend.so      # Patched Weston rdp-backend
│
├── integration/                # Bidirectional Windows <-> Linux integration tools
│   ├── sync-windows-apps.py    # Python scanner generating 220+ .desktop launchers in KDE
│   ├── sync-windows-apps.sh    # Script to sync Windows Start Menu into KDE Kickoff
│   ├── wsl-open.sh             # Drop-in /usr/local/bin/wsl-open replacement
│   ├── user-places.xbel        # KDE Dolphin quick-access places for Windows C:, OneDrive, etc.
│   ├── gtk3-bookmarks          # GTK / XFCE Thunar bookmarks for Windows drives
│   └── check_screens.py        # Wayland multi-monitor geometry validator
│
├── diagnostics/                # Windows Win32 frame and style repair utilities
│   ├── Restore-Windows-Frames.ps1  # General desktop window style restorer
│   └── restore_sccm.ps1            # Targeted restorer for SCCM / MMC consoles
│
├── implementation_plan.md      # Detailed technical architecture plan
└── walkthrough.md              # Project walkthrough and verification notes
```

---

## How to Run
- **Launch Full Desktop Session:** Run `windows-host\scripts\Start-Authentic-Plasma.cmd`
- **Launch System Tray Orchestrator:** Run `windows-host\Run-KWin-Win.cmd`
- **Launch Individual Wayland Apps:** Run `Launch-Dolphin.cmd`, `Launch-Konsole.cmd`, or `Launch-KRunner.cmd`.
