"""Protocol adapter between the Linux foreign-surface model and the host."""

from __future__ import annotations

from typing import Any

from .bridge_protocol import Message, ProtocolError
from .foreign_surface import ForeignSurface, WindowMetadata


class ForeignSurfaceBridge:
    """Translate validated host events into Linux surface state and input."""

    def __init__(self) -> None:
        self.surfaces: dict[str, ForeignSurface] = {}

    def accept_window_created(self, message: Message) -> ForeignSurface:
        self._require_event(message, "window.created")
        metadata = WindowMetadata(
            window_id=self._text(message.payload, "window"),
            application_id=self._text(message.payload, "application"),
            title=self._text(message.payload, "title"),
            width=self._positive_int(message.payload, "width"),
            height=self._positive_int(message.payload, "height"),
            monitor=self._positive_int(message.payload, "monitor"),
        )
        if metadata.window_id in self.surfaces:
            raise ProtocolError("window already has a foreign surface")
        surface = ForeignSurface(metadata)
        self.surfaces[metadata.window_id] = surface
        return surface

    def accept_window_updated(self, message: Message) -> None:
        self._require_event(message, "window.updated")
        window_id = self._text(message.payload, "window")
        surface = self._get_surface(window_id)
        surface.update_metadata(
            WindowMetadata(
                window_id=window_id,
                application_id=surface.metadata.application_id,
                title=str(message.payload.get("title", surface.metadata.title)),
                width=int(message.payload.get("width", surface.metadata.width)),
                height=int(message.payload.get("height", surface.metadata.height)),
                monitor=int(message.payload.get("monitor", surface.metadata.monitor)),
            )
        )

    def remove_window(self, window_id: str) -> None:
        self.surfaces.pop(window_id, None)

    def presentations(self) -> list[dict[str, object]]:
        """Return independently named surfaces for the KDE adapter."""
        return [
            surface.presentation()
            for surface in sorted(self.surfaces.values(), key=lambda item: item.metadata.window_id)
        ]

    def create_pointer_request(self, window_id: str, x: int, y: int, event: str) -> Message:
        surface = self._get_surface(window_id)
        payload = surface.pointer_event(x, y, event)
        return Message(1, f"pointer-{window_id}", "request", "window.pointer", payload)

    def create_keyboard_request(self, window_id: str, key: str, event: str, modifiers: tuple[str, ...] = ()) -> Message:
        payload = self._get_surface(window_id).keyboard_event(key, event, modifiers)
        return Message(1, f"keyboard-{window_id}", "request", "window.keyboard", payload)

    def create_focus_request(self, window_id: str, focused: bool) -> Message:
        payload = self._get_surface(window_id).focus_event(focused)
        return Message(1, f"focus-{window_id}", "request", "window.focus", payload)

    def _get_surface(self, window_id: str) -> ForeignSurface:
        try:
            return self.surfaces[window_id]
        except KeyError as error:
            raise ProtocolError("unknown foreign surface") from error

    @staticmethod
    def _require_event(message: Message, operation: str) -> None:
        if message.kind != "event" or message.operation != operation:
            raise ProtocolError(f"expected {operation} event")

    @staticmethod
    def _text(payload: dict[str, Any] | Any, key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ProtocolError(f"window event requires {key}")
        return value

    @staticmethod
    def _positive_int(payload: dict[str, Any] | Any, key: str) -> int:
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ProtocolError(f"window event requires positive integer {key}")
        return value