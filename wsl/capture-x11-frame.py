#!/usr/bin/env python3
"""Capture one WSLg X11 region and emit an NT-Plasma RGB frame."""

import argparse
import ctypes
import ctypes.util
import struct
import sys


class XImage(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int), ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int), ("format", ctypes.c_int),
        ("data", ctypes.POINTER(ctypes.c_char)), ("byte_order", ctypes.c_int),
        ("bitmap_unit", ctypes.c_int), ("bitmap_bit_order", ctypes.c_int),
        ("bitmap_pad", ctypes.c_int), ("depth", ctypes.c_int),
        ("bytes_per_line", ctypes.c_int), ("bits_per_pixel", ctypes.c_int),
        ("red_mask", ctypes.c_ulong), ("green_mask", ctypes.c_ulong),
        ("blue_mask", ctypes.c_ulong),
    ]


def capture(args: argparse.Namespace) -> bytes:
    x11 = ctypes.CDLL(ctypes.util.find_library("X11"), use_errno=True)
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                              ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
                              ctypes.c_ulong, ctypes.c_int]
    x11.XGetImage.restype = ctypes.POINTER(XImage)
    x11.XDestroyImage.argtypes = [ctypes.POINTER(XImage)]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

    display = x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError("could not open WSLg X11 display")
    image = None
    try:
        root = x11.XDefaultRootWindow(display)
        image = x11.XGetImage(display, root, args.x, args.y, args.width, args.height,
                              0xFFFFFFFF, 2)
        if not image or image.contents.bits_per_pixel not in (24, 32):
            raise RuntimeError("unsupported X11 image format")
        info = image.contents
        raw = ctypes.string_at(info.data, info.bytes_per_line * info.height)
        bytes_per_pixel = info.bits_per_pixel // 8
        pixels = bytearray(args.width * args.height * 3)
        red_shift = _mask_shift(info.red_mask)
        green_shift = _mask_shift(info.green_mask)
        blue_shift = _mask_shift(info.blue_mask)
        offset = 0
        for row in range(args.height):
            row_start = row * info.bytes_per_line
            for column in range(args.width):
                pixel_start = row_start + column * bytes_per_pixel
                value = int.from_bytes(raw[pixel_start:pixel_start + bytes_per_pixel], "little")
                pixels[offset:offset + 3] = bytes((
                    (value >> red_shift) & 255,
                    (value >> green_shift) & 255,
                    (value >> blue_shift) & 255,
                ))
                offset += 3
        return bytes(pixels)
    finally:
        if image:
            x11.XDestroyImage(image)
        x11.XCloseDisplay(display)


def _mask_shift(mask: int) -> int:
    return (mask & -mask).bit_length() - 1 if mask else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--x", type=int, default=0)
    parser.add_argument("--y", type=int, default=0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()
    pixels = capture(args)
    sys.stdout.buffer.write(struct.pack("<iiiii", args.monitor, args.width, args.height,
                                        len(pixels), 0x4E545246))
    sys.stdout.buffer.write(pixels)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())