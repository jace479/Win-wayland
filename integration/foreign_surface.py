"""Linux-side model for a host-owned Windows foreign surface."""

from __future__ import annotations

from dataclasses import dataclass

from .bridge_protocol import ProtocolError


@dataclass(frozen=True)
class WindowMetadata:
    window_id: str
    application_id: str
    title: str
    width: int
    height: int
    monitor: int
    icon: str | None = None

    def __post_init__(self) -> None:
        if not self.window_id or not self.application_id or not self.title:
            raise ProtocolError("window metadata identifiers and title are required")
        if self.width < 1 or self.height < 1 or self.monitor < 1:
            raise ProtocolError("window metadata dimensions and monitor must be positive")
        if self.icon is not None and not isinstance(self.icon, str):
            raise ProtocolError("window icon must be a string or null")


class ForeignSurface:
    """Keep a host window's latest frame and emit normalized input events."""

    def __init__(self, metadata: WindowMetadata) -> None:
        self.metadata = metadata
        self.frame: bytes | None = None

    def update_metadata(self, metadata: WindowMetadata) -> None:
        if metadata.window_id != self.metadata.window_id:
            raise ProtocolError("window identity cannot change during a surface lifetime")
        self.metadata = metadata

    def submit_frame(self, width: int, height: int, pixels: bytes) -> None:
        if width < 1 or height < 1 or len(pixels) != width * height * 3:
            raise ProtocolError("foreign surface frame dimensions or payload are invalid")
        self.frame = bytes(pixels)

    def pointer_event(self, x: int, y: int, event: str) -> dict[str, object]:
        if event not in {"move", "press", "release", "wheel"}:
            raise ProtocolError(f"unsupported pointer event: {event}")
        return {
            "window": self.metadata.window_id,
            "event": event,
            "x": max(0, min(x, self.metadata.width - 1)),
            "y": max(0, min(y, self.metadata.height - 1)),
        }

    def keyboard_event(self, key: str, event: str, modifiers: tuple[str, ...] = ()) -> dict[str, object]:
        if not key or event not in {"press", "release"}:
            raise ProtocolError("keyboard events require a key and valid event")
        if any(not modifier for modifier in modifiers):
            raise ProtocolError("keyboard modifiers must be non-empty strings")
        return {"window": self.metadata.window_id, "event": event, "key": key, "modifiers": list(modifiers)}

    def focus_event(self, focused: bool) -> dict[str, object]:
        return {"window": self.metadata.window_id, "focused": bool(focused)}

    def presentation(self) -> dict[str, object]:
        """Return KDE-facing identity without exposing host execution details."""
        return {
            "window": self.metadata.window_id,
            "application": self.metadata.application_id,
            "title": self.metadata.title,
            "icon": self.metadata.icon,
            "monitor": self.metadata.monitor,
            "width": self.metadata.width,
            "height": self.metadata.height,
        }