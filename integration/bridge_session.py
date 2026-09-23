"""Lifecycle state machine for the NT-Plasma bridge session."""

from __future__ import annotations

from enum import Enum

from .bridge_protocol import ProtocolError


class SessionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    RECOVERING = "recovering"
    STOPPED = "stopped"


class BridgeSession:
    """Enforce the order of bridge lifecycle transitions."""

    def __init__(self) -> None:
        self.state = SessionState.DISCONNECTED

    def connect(self) -> None:
        self._transition(SessionState.DISCONNECTED, SessionState.CONNECTED)

    def authenticate(self) -> None:
        self._transition(SessionState.CONNECTED, SessionState.AUTHENTICATED)

    def mark_ready(self) -> None:
        self._transition(SessionState.AUTHENTICATED, SessionState.READY)

    def disconnect(self) -> None:
        if self.state is SessionState.STOPPED:
            return
        if self.state is SessionState.DISCONNECTED:
            return
        self.state = SessionState.RECOVERING

    def recover(self) -> None:
        self._transition(SessionState.RECOVERING, SessionState.DISCONNECTED)

    def stop(self) -> None:
        if self.state is SessionState.STOPPED:
            return
        self.state = SessionState.STOPPED

    def require_ready(self) -> None:
        if self.state is not SessionState.READY:
            raise ProtocolError("operation requires a ready bridge session")

    def _transition(self, expected: SessionState, target: SessionState) -> None:
        if self.state is not expected:
            raise ProtocolError(
                f"invalid bridge transition: {self.state.value} -> {target.value}"
            )
        self.state = target