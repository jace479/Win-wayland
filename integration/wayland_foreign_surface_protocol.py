"""In-process endpoint for the ntKDE foreign-surface Wayland contract."""

from __future__ import annotations

from dataclasses import dataclass

from .bridge_protocol import ProtocolError
from .desktop_surface_registry import DesktopSurfaceRegistry
from .foreign_surface import WindowMetadata
from .wayland_protocol import validate_frame_sequence, validate_surface_dimensions
from .wayland_surface_adapter import WaylandSurfaceAdapter


@dataclass(frozen=True)
class ProtocolEvent:
    surface_id: str
    name: str
    payload: dict[str, object]


class WaylandForeignSurfaceProtocol:
    """Model the manager and surface requests before native compositor binding."""

    def __init__(self, registry: DesktopSurfaceRegistry) -> None:
        self.registry = registry
        self.adapter = WaylandSurfaceAdapter(registry)
        self._surfaces: set[str] = set()
        self._sequences: dict[str, int | None] = {}
        self._states: dict[str, int] = {}
        self._events: list[ProtocolEvent] = []

    def create_surface(self, surface_id: str) -> None:
        if surface_id in self._surfaces:
            raise ProtocolError("Wayland foreign surface is already bound")
        self.adapter.synchronize()
        self.adapter.role_for(surface_id)
        self._surfaces.add(surface_id)
        self._sequences[surface_id] = None
        self._states[surface_id] = 0

    def destroy(self, surface_id: str) -> None:
        self._require_surface(surface_id)
        self._surfaces.remove(surface_id)
        self._sequences.pop(surface_id, None)
        self._states.pop(surface_id, None)

    def set_metadata(self, surface_id: str, metadata: WindowMetadata) -> None:
        self._require_surface(surface_id)
        self.registry.update_metadata(surface_id, metadata)
        self.adapter.synchronize()

    def attach_frame(
        self, surface_id: str, width: int, height: int, sequence: int, pixels: bytes
    ) -> None:
        self._require_surface(surface_id)
        try:
            validate_surface_dimensions(width, height)
            validate_frame_sequence(self._sequences[surface_id], sequence)
            self.registry.submit_frame(surface_id, width, height, pixels)
        except ProtocolError as error:
            self._events.append(
                ProtocolEvent(surface_id, "frame_rejected", {"sequence": sequence, "reason": str(error)})
            )
            raise
        self._sequences[surface_id] = sequence

    def set_state(self, surface_id: str, state: int) -> None:
        self._require_surface(surface_id)
        if state < 0 or state > 7:
            raise ProtocolError("foreign surface state must be a three-bit mask")
        self._states[surface_id] = state

    def configure(self, surface_id: str, serial: int, width: int, height: int) -> None:
        self._require_surface(surface_id)
        validate_surface_dimensions(width, height)
        self._events.append(
            ProtocolEvent(surface_id, "configure", {"serial": serial, "width": width, "height": height})
        )

    def focus(self, surface_id: str) -> None:
        self._require_surface(surface_id)
        self._events.append(ProtocolEvent(surface_id, "focus", {}))

    def close(self, surface_id: str) -> None:
        self._require_surface(surface_id)
        self._events.append(ProtocolEvent(surface_id, "close", {}))

    def events(self) -> tuple[ProtocolEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events

    def _require_surface(self, surface_id: str) -> None:
        if surface_id not in self._surfaces:
            raise ProtocolError("Wayland foreign surface is not bound")