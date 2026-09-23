# KDE configuration

Windows drives are exposed through the normal Dolphin Places file at
`~/.local/share/user-places.xbel`. The synchronizer adds available WSL DrvFs
mounts such as `/mnt/c` as ordinary `C:` locations while preserving native
Linux places and removing only entries it previously managed.
