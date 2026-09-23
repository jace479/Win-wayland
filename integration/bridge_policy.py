"""Authorization policy for host operations exposed to the Linux bridge."""

from __future__ import annotations

from dataclasses import dataclass

from .bridge_protocol import ProtocolError


@dataclass(frozen=True)
class OperationPolicy:
    operation: str
    privileged: bool


POLICIES = {
    "app.launch": OperationPolicy("app.launch", privileged=False),
    "window.focus": OperationPolicy("window.focus", privileged=False),
    "app.list": OperationPolicy("app.list", privileged=False),
    "identity.session": OperationPolicy("identity.session", privileged=False),
    "identity.sso-request": OperationPolicy("identity.sso-request", privileged=False),
    "desktop.shutdown": OperationPolicy("desktop.shutdown", privileged=False),
    "host.restart-bridge": OperationPolicy("host.restart-bridge", privileged=True),
}


def authorize_operation(operation: str, privileged_capability: bool) -> OperationPolicy:
    """Resolve an operation and require an explicit privilege capability."""
    policy = POLICIES.get(operation)
    if policy is None:
        raise ProtocolError(f"operation is not allow-listed: {operation}")
    if policy.privileged and not privileged_capability:
        raise ProtocolError(f"privileged capability is required: {operation}")
    return policy