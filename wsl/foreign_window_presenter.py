#!/usr/bin/env python3
"""
ntKDE Foreign Window Presenter (Path B - Zero-TCP)
Receives live Win32/UWP frames over an in-kernel pipe stream (anonymous pipe / stdio or named pipe),
creates a native KDE window with KDE Breeze decorations, renders the frames, and forwards
pointer and keyboard input back across the pipe to the Windows host.
STRICTLY ZERO TCP/IP: Uses kernel pipe streams with zero network port exposure.
"""

from __future__ import annotations

import os
import struct
import sys
import threading
from typing import Optional

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False
    QtCore = None
    QtGui = None
    QtWidgets = None


MAGIC_NTFR = 0x4E545246


def map_qt_key_to_vk(key: int, text: str = "") -> int:
    """Map Qt key code to Win32 Virtual Key code."""
    # Letters A-Z
    if 0x41 <= key <= 0x5A:
        return int(key)
    # Numbers 0-9
    if 0x30 <= key <= 0x39:
        return int(key)
    # Return / Enter (Qt::Key_Return = 0x01000004, Qt::Key_Enter = 0x01000005)
    if key in (0x01000004, 0x01000005):
        return 0x0D
    # Backspace (Qt::Key_Backspace = 0x01000003)
    if key == 0x01000003:
        return 0x08
    # Tab (Qt::Key_Tab = 0x01000001)
    if key == 0x01000001:
        return 0x09
    # Space (Qt::Key_Space = 0x20)
    if key == 0x20:
        return 0x20
    # Escape (Qt::Key_Escape = 0x01000000)
    if key == 0x01000000:
        return 0x1B
    # Delete (Qt::Key_Delete = 0x01000007)
    if key in (0x01000007, 0x2E):
        return 0x2E
    # Arrow keys (Qt::Key_Left = 0x01000012, etc.)
    if key in (0x01000012, 0x25):
        return 0x25
    if key in (0x01000013, 0x26):
        return 0x26
    if key in (0x01000014, 0x27):
        return 0x27
    if key in (0x01000015, 0x28):
        return 0x28
    if text and len(text) == 1:
        return ord(text.upper())
    return 0


_BaseWidget = QtWidgets.QWidget if HAS_PYQT5 else object
_BaseWindow = QtWidgets.QMainWindow if HAS_PYQT5 else object


class ForeignSurfaceWidget(_BaseWidget):
    frame_received = QtCore.pyqtSignal(int, int, bytes) if HAS_PYQT5 else None

    def __init__(self, parent=None):
        if HAS_PYQT5:
            super().__init__(parent)
            self.image: Optional[QtGui.QImage] = None
            self.frame_received.connect(self.on_frame_received)
            self.setMouseTracking(True)
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.send_command_fn = None
        self._initial_size_set = False

    def on_frame_received(self, width: int, height: int, pixels: bytes):
        if not HAS_PYQT5:
            return
        # Format_BGR888 corresponds to Windows 24bpp RGB
        self.image = QtGui.QImage(pixels, width, height, width * 3, QtGui.QImage.Format_BGR888)
        if not self._initial_size_set and width > 100 and height > 100:
            self._initial_size_set = True
            if self.window():
                self.window().resize(width, height)
        self.update()

    def paintEvent(self, event):
        if not HAS_PYQT5:
            return
        painter = QtGui.QPainter(self)
        if self.image and not self.image.isNull():
            if self.width() == self.image.width() and self.height() == self.image.height():
                painter.drawImage(0, 0, self.image)
            else:
                scaled = self.image.scaled(self.size(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
                painter.drawImage(0, 0, scaled)
        else:
            painter.fillRect(self.rect(), QtGui.QColor(35, 38, 41))
            painter.setPen(QtGui.QColor(239, 240, 241))
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "Waiting for Windows application frame...")

    def _map_coords(self, x: float, y: float):
        if self.image and not self.image.isNull() and self.width() > 0 and self.height() > 0:
            scale_x = self.image.width() / self.width()
            scale_y = self.image.height() / self.height()
            return int(x * scale_x), int(y * scale_y)
        return int(x), int(y)

    def mouseMoveEvent(self, event):
        if self.send_command_fn:
            x, y = self._map_coords(event.x(), event.y())
            self.send_command_fn(f"INPUT|POINTER|move|{x}|{y}\n")

    def mousePressEvent(self, event):
        if HAS_PYQT5:
            self.setFocus()
        if self.send_command_fn:
            x, y = self._map_coords(event.x(), event.y())
            btn = "right" if event.button() == QtCore.Qt.RightButton else "left"
            self.send_command_fn(f"INPUT|POINTER|press|{x}|{y}|{btn}\n")

    def mouseReleaseEvent(self, event):
        if self.send_command_fn:
            x, y = self._map_coords(event.x(), event.y())
            btn = "right" if event.button() == QtCore.Qt.RightButton else "left"
            self.send_command_fn(f"INPUT|POINTER|release|{x}|{y}|{btn}\n")

    def mouseDoubleClickEvent(self, event):
        if HAS_PYQT5:
            self.setFocus()
        if self.send_command_fn:
            x, y = self._map_coords(event.x(), event.y())
            btn = "right" if event.button() == QtCore.Qt.RightButton else "left"
            self.send_command_fn(f"INPUT|POINTER|dblclk|{x}|{y}|{btn}\n")

    def wheelEvent(self, event):
        if self.send_command_fn:
            delta = event.angleDelta().y() if hasattr(event, "angleDelta") else 120
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            x, y = self._map_coords(pos.x(), pos.y())
            self.send_command_fn(f"INPUT|POINTER|wheel|{x}|{y}|{int(delta)}\n")

    def keyPressEvent(self, event):
        if self.send_command_fn:
            text = event.text()
            if text and len(text) == 1 and ord(text) >= 32:
                self.send_command_fn(f"INPUT|CHAR|{text}\n")
            else:
                vk = self._map_key_to_vk(event.key(), text)
                if vk:
                    self.send_command_fn(f"INPUT|KEY|press|{vk}\n")

    def keyReleaseEvent(self, event):
        vk = self._map_key_to_vk(event.key(), event.text())
        if self.send_command_fn and vk:
            self.send_command_fn(f"INPUT|KEY|release|{vk}\n")

    @staticmethod
    def _map_key_to_vk(key: int, text: str) -> int:
        return map_qt_key_to_vk(key, text)


class ForeignWindow(_BaseWindow):
    def __init__(self, mode: str = "stdio", pipe_name: Optional[str] = None, title: str = "ntKDE - Windows Application"):
        super().__init__()
        self.setWindowTitle(title)
        app_id = title.split(" ")[0].lower() if title else "winapp"
        self.setObjectName(f"ntkde_{app_id}")
        self.surface = ForeignSurfaceWidget(self)
        self.setCentralWidget(self.surface)
        self.resize(800, 600)

        self.mode = mode
        self.pipe_name = pipe_name
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.pipe_stream = None

        self.surface.send_command_fn = self.send_command
        self.start_receiver()

    def resizeEvent(self, event):
        if HAS_PYQT5:
            super().resizeEvent(event)
        if self.running:
            w = event.size().width()
            h = event.size().height()
            if w > 50 and h > 50:
                self.send_command(f"INPUT|RESIZE|{w}|{h}\n")

    def changeEvent(self, event):
        if HAS_PYQT5:
            super().changeEvent(event)
            if hasattr(QtCore, "QEvent") and event.type() == QtCore.QEvent.WindowStateChange and self.running:
                if self.isMinimized():
                    self.send_command("INPUT|STATE|minimize\n")
                elif self.isMaximized():
                    self.send_command("INPUT|STATE|maximize\n")

    def start_receiver(self):
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()

    def _stream_loop(self):
        header_struct = struct.Struct("<iiiii")
        header_size = header_struct.size

        if self.mode == "pipe" and self.pipe_name:
            try:
                self.pipe_stream = open(self.pipe_name, "r+b", buffering=0)
                in_stream = self.pipe_stream
            except Exception as e:
                print(f"[foreign_window_presenter] Failed to open named pipe: {e}", file=sys.stderr)
                return
        else:
            in_stream = sys.stdin.buffer

        while self.running:
            try:
                header_bytes = self._read_exact(in_stream, header_size)
                if not header_bytes:
                    break

                window_id, width, height, payload_length, magic = header_struct.unpack(header_bytes)
                if magic != MAGIC_NTFR or width < 1 or height < 1 or payload_length != width * height * 3:
                    print(f"[foreign_window_presenter] Invalid frame format: magic={hex(magic)} {width}x{height}", file=sys.stderr)
                    break

                pixel_bytes = self._read_exact(in_stream, payload_length)
                if not pixel_bytes:
                    break

                self.surface.frame_received.emit(width, height, pixel_bytes)

            except Exception as ex:
                print(f"[foreign_window_presenter] Read error: {ex}", file=sys.stderr)
                break

    def _read_exact(self, stream, length: int) -> Optional[bytes]:
        buffer = bytearray(length)
        view = memoryview(buffer)
        received = 0
        while received < length and self.running:
            try:
                n = stream.readinto(view[received:])
                if n == 0 or n is None:
                    return None
                received += n
            except Exception:
                return None
        return bytes(buffer)

    def send_command(self, cmd: str):
        try:
            data = cmd.encode("utf-8")
            if self.mode == "pipe" and self.pipe_stream:
                self.pipe_stream.write(data)
                self.pipe_stream.flush()
            else:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
        except Exception:
            pass

    def closeEvent(self, event):
        self.running = False
        self.send_command("INPUT|CLOSE\n")
        if self.pipe_stream:
            try:
                self.pipe_stream.close()
            except Exception:
                pass
        if hasattr(event, "accept"):
            event.accept()


def verify_stream(num_frames: int = 2, mode: str = "stdio", pipe_name: Optional[str] = None) -> bool:
    """Headless zero-TCP verification helper: reads num_frames NTFR frames from pipe/stdio and sends INPUT."""
    header_struct = struct.Struct("<iiiii")
    if mode == "pipe" and pipe_name:
        stream = open(pipe_name, "r+b", buffering=0)
        in_stream = stream
        out_stream = stream
    else:
        in_stream = sys.stdin.buffer
        out_stream = sys.stdout.buffer

    for _ in range(num_frames):
        header_bytes = bytearray(header_struct.size)
        view = memoryview(header_bytes)
        rec = 0
        while rec < header_struct.size:
            n = in_stream.readinto(view[rec:])
            if n == 0 or n is None:
                raise EOFError("Stream closed while reading header")
            rec += n
        window_id, width, height, payload_length, magic = header_struct.unpack(header_bytes)
        if magic != MAGIC_NTFR:
            raise ValueError(f"Invalid magic: {hex(magic)}")
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid dimensions: {width}x{height}")
        if payload_length != width * height * 3:
            raise ValueError(f"Invalid payload length: {payload_length} != {width * height * 3}")
        payload = bytearray(payload_length)
        view_p = memoryview(payload)
        rec_p = 0
        while rec_p < payload_length:
            n = in_stream.readinto(view_p[rec_p:])
            if n == 0 or n is None:
                raise EOFError("Stream closed while reading payload")
            rec_p += n

    # Send test input back over out_stream
    out_stream.write(b"INPUT|POINTER|move|10|10\n")
    out_stream.flush()
    return True


def main():
    mode = "stdio"
    pipe_name = None
    title = "Windows Application (ntKDE)"

    args = sys.argv[1:]
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg in ("--stdio", "stdio"):
            mode = "stdio"
        elif arg in ("--pipe", "-p") and idx + 1 < len(args):
            mode = "pipe"
            pipe_name = args[idx + 1]
            idx += 1
        elif not arg.startswith("-"):
            title = arg
        idx += 1

    if "--verify" in sys.argv or "--verify-frames" in sys.argv:
        frames = 2
        for i, arg in enumerate(sys.argv):
            if arg == "--verify-frames" and i + 1 < len(sys.argv):
                try:
                    frames = int(sys.argv[i + 1])
                except ValueError:
                    pass
        print(f"[foreign_window_presenter] Verifying {frames} frames over {mode}...", file=sys.stderr)
        ok = verify_stream(num_frames=frames, mode=mode, pipe_name=pipe_name)
        if ok:
            print(f"[foreign_window_presenter] SUCCESS: verified {frames} frames.", file=sys.stderr)
            return 0
        return 1

    if not HAS_PYQT5:
        print("[ntKDE] Error: PyQt5 is required to run foreign_window_presenter GUI.", file=sys.stderr)
        return 1

    if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("ntKDE Foreign Window")

    window = ForeignWindow(mode=mode, pipe_name=pipe_name, title=title)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
