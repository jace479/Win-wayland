"""KDE-facing registry for Linux and Windows desktop surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from .bridge_protocol import ProtocolError
from .foreign_surface import ForeignSurface, WindowMetadata


@dataclass(frozen=True)
class DesktopSurfaceRecord:
    surface_id: str
    origin: str
    application: str
    title: str
    icon: str | None
    monitor: int
    width: int
    height: int
    has_frame: bool


class DesktopSurfaceRegistry:
    """Expose independently named foreign surfaces to a desktop adapter."""

    def __init__(self) -> None:
        self._surfaces: dict[str, ForeignSurface] = {}

    def add_foreign_surface(self, surface: ForeignSurface) -> None:
        surface_id = surface.metadata.window_id
        if surface_id in self._surfaces:
            raise ProtocolError("desktop surface is already registered")
        self._surfaces[surface_id] = surface

    def remove(self, surface_id: str) -> None:
        self._surfaces.pop(surface_id, None)

    def surface(self, surface_id: str) -> ForeignSurface:
        try:
            return self._surfaces[surface_id]
        except KeyError as error:
            raise ProtocolError("desktop surface is not registered") from error

    def update_metadata(self, surface_id: str, metadata: WindowMetadata) -> None:
        self.surface(surface_id).update_metadata(metadata)

    def submit_frame(self, surface_id: str, width: int, height: int, pixels: bytes) -> None:
        self.surface(surface_id).submit_frame(width, height, pixels)

    def records(self) -> list[DesktopSurfaceRecord]:
        return [
            DesktopSurfaceRecord(
                surface_id=surface.metadata.window_id,
                origin="windows",
                application=surface.metadata.application_id,
                title=surface.metadata.title,
                icon=surface.metadata.icon,
                monitor=surface.metadata.monitor,
                width=surface.metadata.width,
                height=surface.metadata.height,
                has_frame=surface.frame is not None,
            )
            for surface in sorted(self._surfaces.values(), key=lambda item: item.metadata.window_id)
        ]

    def pointer_request(self, surface_id: str, x: int, y: int, event: str) -> dict[str, object]:
        return self.surface(surface_id).pointer_event(x, y, event)