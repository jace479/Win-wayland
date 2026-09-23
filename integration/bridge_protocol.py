"""Typed protocol primitives for the NT-Plasma host and desktop bridges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


PROTOCOL_VERSION = 1
MESSAGE_KINDS = frozenset({"request", "response", "event", "error"})


class ProtocolError(ValueError):
    """Raised when a bridge message does not satisfy the protocol."""


@dataclass(frozen=True)
class Message:
    version: int
    message_id: str
    kind: str
    operation: str
    payload: Mapping[str, Any]
    deadline: str | None = None

    def __post_init__(self) -> None:
        if self.version != PROTOCOL_VERSION:
            raise ProtocolError(f"unsupported protocol version: {self.version}")
        if not self.message_id or not isinstance(self.message_id, str):
            raise ProtocolError("message id must be a non-empty string")
        if self.kind not in MESSAGE_KINDS:
            raise ProtocolError(f"unsupported message kind: {self.kind}")
        if not self.operation or not isinstance(self.operation, str):
            raise ProtocolError("operation must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise ProtocolError("payload must be an object")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "version": self.version,
            "id": self.message_id,
            "kind": self.kind,
            "operation": self.operation,
            "payload": dict(self.payload),
        }
        if self.deadline is not None:
            result["deadline"] = self.deadline
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Message":
        required = {"version", "id", "kind", "operation", "payload"}
        missing = required.difference(value)
        if missing:
            raise ProtocolError(f"missing message fields: {sorted(missing)}")
        return cls(
            version=value["version"],
            message_id=value["id"],
            kind=value["kind"],
            operation=value["operation"],
            payload=value["payload"],
            deadline=value.get("deadline"),
        )


def negotiate_capabilities(
    local: Mapping[str, Any], remote: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the mutually supported capabilities without enabling extras."""
    local_capabilities = set(local.get("capabilities", ()))
    remote_capabilities = set(remote.get("capabilities", ()))
    return {
        "version": PROTOCOL_VERSION,
        "capabilities": sorted(local_capabilities & remote_capabilities),
    }


def validate_application_request(
    payload: Mapping[str, Any], allow_list: Mapping[str, str]
) -> str:
    """Resolve an application identifier through an explicit host allow-list."""
    application_id = payload.get("application")
    if not isinstance(application_id, str) or application_id not in allow_list:
        raise ProtocolError("application is not present in the host allow-list")
    return allow_list[application_id]