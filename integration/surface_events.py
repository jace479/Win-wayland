"""Wire-format events for Windows surfaces presented to the Linux bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bridge_protocol import Message, ProtocolError
from .foreign_surface import WindowMetadata


@dataclass(frozen=True)
class SurfaceEventFactory:
    """Create typed host events without exposing HWND values to Linux."""

    @staticmethod
    def created(metadata: WindowMetadata) -> Message:
        return Message(1, f"window-created-{metadata.window_id}", "event", "window.created", _metadata_payload(metadata))

    @staticmethod
    def updated(metadata: WindowMetadata) -> Message:
        return Message(1, f"window-updated-{metadata.window_id}", "event", "window.updated", _metadata_payload(metadata))

    @staticmethod
    def destroyed(window_id: str) -> Message:
        if not window_id:
            raise ProtocolError("destroyed surface requires a window ID")
        return Message(1, f"window-destroyed-{window_id}", "event", "window.destroyed", {"window": window_id})


def _metadata_payload(metadata: WindowMetadata) -> dict[str, Any]:
    return {"window": metadata.window_id, "application": metadata.application_id, "title": metadata.title, "width": metadata.width, "height": metadata.height, "monitor": metadata.monitor, "icon": metadata.icon}