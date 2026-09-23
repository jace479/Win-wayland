"""Identity and SSO policy; credentials never cross the bridge."""

from __future__ import annotations

from .bridge_protocol import ProtocolError


IDENTITY_CAPABILITIES = frozenset({"session-identity", "sso-request"})


def authorize_identity_request(capability: str, authenticated: bool) -> str:
    """Authorize an identity operation without accepting passwords or tokens."""
    if not authenticated:
        raise ProtocolError("identity request requires an authenticated session")
    if capability not in IDENTITY_CAPABILITIES:
        raise ProtocolError(f"identity capability is not supported: {capability}")
    return capability