"""Challenge-response authentication primitives for the local bridge."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from .bridge_protocol import ProtocolError


def create_challenge() -> str:
    """Create a URL-safe nonce suitable for one authentication attempt."""
    return secrets.token_urlsafe(32)


def create_proof(secret: bytes, challenge: str) -> str:
    """Create an HMAC proof without exposing the shared secret."""
    if not secret or not challenge:
        raise ProtocolError("authentication secret and challenge are required")
    return hmac.new(secret, challenge.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_proof(secret: bytes, challenge: str, proof: str) -> bool:
    """Verify a proof in constant time."""
    try:
        expected = create_proof(secret, challenge)
    except (ProtocolError, UnicodeError):
        return False
    return hmac.compare_digest(expected, proof)