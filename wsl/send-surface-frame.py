#!/usr/bin/env python3
"""Send a synthetic WSL surface frame to the Windows host prototype."""

import socket
import sys


def get_host_address() -> str:
    """Use WSL's default gateway to reach the Windows host."""
    with open("/proc/net/route", encoding="ascii") as routes:
        for line in routes:
            fields = line.split()
            if len(fields) > 2 and fields[1] == "00000000":
                gateway = int(fields[2], 16)
                return socket.inet_ntoa(gateway.to_bytes(4, "little"))
    raise RuntimeError("WSL default gateway was not found")


def main() -> int:
    monitor = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 1920
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    red = int(sys.argv[4]) if len(sys.argv) > 4 else 32
    green = int(sys.argv[5]) if len(sys.argv) > 5 else 96
    blue = int(sys.argv[6]) if len(sys.argv) > 6 else 160
    frame = f"FRAME|{monitor}|{width}|{height}|{red}|{green}|{blue}\n"
    if "--raw" in sys.argv:
        import struct

        pixels = bytes((red, green, blue)) * (width * height)
        sys.stdout.buffer.write(struct.pack("<iiiii", monitor, width, height, len(pixels), 0x4E545246))
        sys.stdout.buffer.write(pixels)
        sys.stdout.buffer.flush()
        return 0
    if "--stdio" in sys.argv:
        print(frame, end="", flush=True)
        return 0
    with socket.create_connection((get_host_address(), 49173), timeout=5) as connection:
        connection.sendall(frame.encode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())