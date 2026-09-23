"""Validation helpers for the NT-Plasma foreign-surface protocol draft."""

from __future__ import annotations

from .bridge_protocol import ProtocolError


def validate_frame_sequence(previous: int | None, sequence: int) -> None:
    """Require strictly increasing frame sequence numbers."""
    if sequence < 0 or (previous is not None and sequence <= previous):
        raise ProtocolError("foreign surface frame sequence is not increasing")


def validate_surface_dimensions(width: int, height: int) -> None:
    """Reject zero or unreasonably large compositor buffers."""
    if not (1 <= width <= 16384 and 1 <= height <= 16384):
        raise ProtocolError("foreign surface dimensions are outside the supported range")