# Phase 1 Recommendation: KDE Plasma through WSLg

## Why

WSLg is the supported Windows 11 path for displaying Linux GUI applications.
Using it avoids unsupported kernel changes and lets Windows remain responsible
for authentication, drivers, DWM, and native applications.

## Risks

Full Plasma is not a supported WSL desktop shell. Session startup, window
management, input, audio, performance, and package updates may regress.
Installing a display manager can conflict with WSL, so Phase 1 launches Plasma
directly and does not use SDDM.

## Alternatives

Use individual Linux GUI applications only; use a third-party X server; or
run Plasma in a VM. These are less integrated, less reversible, or outside
the project's primary WSL2 direction.

## Test

First launch a simple WSLg application, then launch the Plasma session using
`wsl/plasma-launch.sh`. Record startup logs and complete the acceptance matrix
in [../testing/phase1-test-plan.md](../testing/phase1-test-plan.md).

## Rollback

Run `powershell/Unregister-PlasmaAutostartTask.ps1`, then stop or unregister
the test distro. Windows Explorer and the Windows logon path remain unchanged.
