"""Bounded newline-delimited transport for bridge messages."""

from __future__ import annotations

import json
from typing import BinaryIO

from .bridge_protocol import Message, ProtocolError


MAX_MESSAGE_BYTES = 1024 * 1024


def encode_message(message: Message) -> bytes:
    """Serialize one message with a bounded, deterministic wire format."""
    encoded = json.dumps(
        message.to_dict(), ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message exceeds maximum size")
    return encoded + b"\n"


def read_message(stream: BinaryIO) -> Message:
    """Read one complete message and reject oversized or malformed input."""
    encoded = stream.readline(MAX_MESSAGE_BYTES + 1)
    if not encoded:
        raise EOFError("bridge connection closed")
    if len(encoded) > MAX_MESSAGE_BYTES or not encoded.endswith(b"\n"):
        raise ProtocolError("message is missing a bounded newline terminator")
    try:
        value = json.loads(encoded)
    except json.JSONDecodeError as error:
        raise ProtocolError("message is not valid JSON") from error
    if not isinstance(value, dict):
        raise ProtocolError("message must be a JSON object")
    return Message.from_dict(value)