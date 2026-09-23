# ntKDE

ntKDE is a desktop shell replacement for Windows. It is not a Linux
distribution, virtualization project, or WSL frontend.

The objective is to make KDE Plasma the primary user experience while Windows
remains the underlying operating system.

Windows remains responsible for the kernel, drivers, security, Active
Directory, gaming compatibility, Windows application compatibility, and
Windows Update. KDE provides the desktop, panels, launcher, widgets, file
management, and user workflows.

The user should primarily interact with KDE and should not need Explorer.

```text
Windows NT
    |
ntKDE Translation Layer
    |
KDE Plasma
    |
Windows Applications + Linux Applications
```

Applications from WinGet, APT, Flatpak, and MSIX should appear as one unified
software ecosystem. Examples include PowerShell, Visual Studio Code, Steam,
Dolphin, Kate, Discord, and Firefox.

Every application is intended to be a first-class KDE citizen. Regardless of
origin, applications share the same launcher, icons, decorations, task
management, focus, input, accessibility, notifications, and recovery behavior.

## Current Prototype

The current implementation uses Ubuntu WSL2 and WSLg to validate application
catalog synchronization, Windows application launching, KDE integration, and
bridge protocols. WSLg proves that KDE components can execute on Windows, but
it is not the final desktop architecture because it exports panels and desktop
surfaces as independent windows.

The final architecture must present KDE as one unified shell experience.

As the Explorer replacement, ntKDE must provide the complete user-facing
desktop contract, not only application launching and window composition. This
includes the desktop and wallpaper, panels, task manager, window switching,
system tray, notifications, search, settings, file workflows, drive access,
process visibility, session actions, accessibility, and recovery. Windows
processes and background tasks remain owned by Windows, but KDE must receive a
sanitized task/process model so users can manage the whole session from KDE.

## Success Criteria

A user should be able to log into Windows, see KDE Plasma, browse with Dolphin,
launch Notepad, PowerShell, Steam, and Linux applications, and install software
through one software center without opening Explorer.

## Design Goals

- Explorer replacement
- Unified software catalog and launcher
- Windows and Linux application integration
- KDE-first user experience
- Native Windows and enterprise compatibility
- Full Windows shell capabilities through KDE-owned equivalents
- Unified visible-window and background-process management

## Non-Goals

- Replacing the Windows kernel
- Running Windows applications through Wine
- Re-implementing Windows APIs
- Building a Linux distribution

## Prototype Architecture

The shell lifecycle and recovery contract is defined in
[docs/architecture/ntkde-shell-lifecycle.md](docs/architecture/ntkde-shell-lifecycle.md).
Explorer replacement remains disabled until its shell-mode gates pass.

ntKDE is an experimental unified desktop project:

- Windows 11 remains the host OS and owns hardware, authentication, drivers,
  Active Directory, and native Windows application compatibility.
- Ubuntu WSL2 provides the Linux userland.
- KDE Plasma provides the primary interactive workspace through WSLg.

Phase 1 is successful when Ubuntu and Plasma start automatically, both Windows
and Linux applications can be launched from KDE, and representative daily
desktop tasks can be completed without opening Explorer.

The long-term vision is a KDE-first desktop hosted by Windows Server Core:
Windows remains responsible for login, hardware, security, drivers, and native
Windows processes, while KDE Plasma provides the primary user-facing desktop.
The WSLg implementation is an integration prototype toward that goal, not the
final desktop surface.

## Status

This repository contains the initial design and scaffold. Phase 1 is
intentionally reversible and does not replace Winlogon, DWM, or Explorer.
Phase 1.1 will harden startup and test cross-platform integration before a
dedicated desktop display architecture is selected for the Server Core target.

## Repository map

| Directory | Purpose |
|---|---|
| `docs/` | Architecture, decisions, testing, and rollback documentation |
| `scripts/` | Cross-platform orchestration |
| `powershell/` | Windows provisioning and logon automation |
| `wsl/` | Ubuntu provisioning and Plasma launch scripts |
| `kde/` | KDE configuration and desktop entries |
| `integration/` | Future clipboard, notification, and file integration |
| `prototypes/` | Disposable proof-of-concept experiments |
| `installer/` | Future packaged installer |

## Phase 1 safety boundary

Run on a disposable or non-critical Windows 11 test machine first. The
automation creates a WSL distro configuration and an optional per-user
Scheduled Task; it does not alter the Windows shell or kernel.

See [docs/architecture/phase1-wslg-plasma.md](docs/architecture/phase1-wslg-plasma.md)
and [docs/testing/phase1-test-plan.md](docs/testing/phase1-test-plan.md).
