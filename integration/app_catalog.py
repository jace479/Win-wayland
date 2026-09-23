"""Host-owned application catalog exposed to the KDE desktop bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .bridge_protocol import ProtocolError


@dataclass(frozen=True)
class ApplicationEntry:
    """A safe, displayable application record; launch policy stays on the host."""

    application_id: str
    display_name: str
    executable: str
    arguments: tuple[str, ...] = ()
    category: str = "Other"
    origin: str = "linux"
    icon: str | None = None

    def __post_init__(self) -> None:
        for value, field in (
            (self.application_id, "application id"),
            (self.display_name, "display name"),
            (self.executable, "executable"),
            (self.category, "category"),
            (self.origin, "origin"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProtocolError(f"{field} must be a non-empty string")
        if any(not isinstance(argument, str) for argument in self.arguments):
            raise ProtocolError("application arguments must be strings")
        if self.icon is not None and not isinstance(self.icon, str):
            raise ProtocolError("application icon must be a string or null")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.application_id,
            "name": self.display_name,
            "category": self.category,
            "origin": self.origin,
            "arguments": list(self.arguments),
        }
        if self.icon is not None:
            result["icon"] = self.icon
        return result


class ApplicationCatalog:
    """Maintain host-owned entries without exposing executable paths to KDE."""

    def __init__(self, entries: tuple[ApplicationEntry, ...] = ()) -> None:
        self._entries = {entry.application_id: entry for entry in entries}

    def add(self, entry: ApplicationEntry) -> None:
        if entry.application_id in self._entries:
            raise ProtocolError(f"duplicate application id: {entry.application_id}")
        self._entries[entry.application_id] = entry

    def list_for_desktop(self) -> list[dict[str, Any]]:
        return [
            entry.to_dict()
            for entry in sorted(self._entries.values(), key=lambda item: item.display_name.casefold())
        ]

    def merge(self, entries: tuple[ApplicationEntry, ...]) -> None:
        """Merge a second app source while rejecting ID collisions."""
        for entry in entries:
            self.add(entry)

    def resolve(self, application_id: str) -> ApplicationEntry:
        try:
            return self._entries[application_id]
        except KeyError as error:
            raise ProtocolError("application is not present in the host catalog") from error