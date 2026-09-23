"""Compositor-neutral adapter for presenting ntKDE foreign surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bridge_protocol import ProtocolError
from .desktop_surface_registry import DesktopSurfaceRegistry, DesktopSurfaceRecord


@dataclass(frozen=True)
class WaylandSurfaceRole:
    surface_id: str
    application: str
    title: str
    icon: str | None
    monitor: int
    width: int
    height: int


class WaylandSurfaceAdapter:
    """Map registry records to Wayland foreign-surface roles."""

    def __init__(self, registry: DesktopSurfaceRegistry) -> None:
        self.registry = registry
        self.roles: dict[str, WaylandSurfaceRole] = {}

    def synchronize(self) -> tuple[WaylandSurfaceRole, ...]:
        """Create/update roles and remove roles whose registry surface vanished."""
        records = {record.surface_id: record for record in self.registry.records()}
        self.roles = {
            surface_id: self._role(record)
            for surface_id, record in records.items()
        }
        return tuple(self.roles.values())

    def role_for(self, surface_id: str) -> WaylandSurfaceRole:
        try:
            return self.roles[surface_id]
        except KeyError as error:
            raise ProtocolError("Wayland role does not exist for surface") from error

    def frame_descriptor(self, surface_id: str) -> dict[str, Any]:
        role = self.role_for(surface_id)
        record = next(
            record for record in self.registry.records() if record.surface_id == surface_id
        )
        return {
            "surface": role.surface_id,
            "width": role.width,
            "height": role.height,
            "has_frame": record.has_frame,
            "format": "BGR24",
        }

    def pointer(self, surface_id: str, x: int, y: int, event: str) -> dict[str, object]:
        self.role_for(surface_id)
        return self.registry.pointer_request(surface_id, x, y, event)

    @staticmethod
    def _role(record: DesktopSurfaceRecord) -> WaylandSurfaceRole:
        if record.origin != "windows":
            raise ProtocolError("foreign Wayland role requires a Windows surface")
        return WaylandSurfaceRole(
            surface_id=record.surface_id,
            application=record.application,
            title=record.title,
            icon=record.icon,
            monitor=record.monitor,
            width=record.width,
            height=record.height,
        )