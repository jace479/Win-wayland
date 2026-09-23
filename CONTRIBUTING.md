# Contributing

Keep changes modular, reversible, and documented. Prefer PowerShell for
Windows automation and Bash for Ubuntu automation. Scripts must accept
parameters instead of assuming a username, distro name, or installation path.

Every behavioral change should update the relevant test or rollback procedure.
Do not modify the Windows kernel, Winlogon, DWM, or Explorer as part of Phase 1.
