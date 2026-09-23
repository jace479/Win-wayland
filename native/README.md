# Native Wayland Protocol Build

This directory is the native binding boundary for the foreign-surface protocol.
It intentionally does not contain generated files. `build-protocol.sh` uses
Ubuntu's `wayland-scanner` to generate client and server protocol sources from
the canonical XML document.

Install the development prerequisites in Ubuntu before running it:

```bash
sudo apt install libwayland-dev wayland-protocols
```

The generated files are written below `native/build/generated/` and are not
required by the Python integration tests. A Weston or KWin implementation is
the next consumer of the server-side generated interface.