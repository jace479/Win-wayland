# COPILOT.md

# NT-Plasma

## Purpose

NT-Plasma is an experimental desktop environment project that aims to combine:

- Windows NT as the host operating system
- Ubuntu running inside WSL2 as the primary Linux userland
- KDE Plasma as the primary user-facing desktop shell
- Native Windows application compatibility
- Native Linux application support

The goal is to provide a KDE-centric desktop experience without replacing the Windows kernel.

Windows remains responsible for:

- Hardware drivers
- Security
- Authentication
- Active Directory
- Group Policy
- Windows application execution
- Device management

Ubuntu and KDE provide the user experience.

---

# Project Vision

The desired architecture is:

```text
Windows NT
├── Winlogon
├── DWM
├── Native Windows Applications
└── NT-Plasma Launcher
    └── WSL2 Ubuntu
        ├── KDE Plasma
        ├── Linux Applications
        └── Integration Services

        