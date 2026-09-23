# NT-Plasma Architecture Overview

Windows 11 remains the host OS. Winlogon authenticates the user, Windows owns
drivers and device management, DWM presents native Windows windows, and native
Windows applications continue to run normally.

The NT-Plasma launcher starts an Ubuntu WSL2 distribution. WSLg supplies the
supported Wayland/X11 and audio bridge used by KDE Plasma and Linux GUI
applications. KDE is the primary workspace for the proof of concept; it is not
yet a Windows shell replacement.

This boundary keeps the experiment reversible: removing the launcher task and
unregistering the distro restores the normal Windows desktop.
