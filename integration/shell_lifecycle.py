"""Safe ntKDE shell-mode lifecycle and recovery state machine."""

from __future__ import annotations

import json
import os
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bridge_protocol import ProtocolError

# Default persistence path under XDG state directory
_DEFAULT_STATE_DIR = Path(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
) / "nt-plasma"
_DEFAULT_LIFECYCLE_PATH = _DEFAULT_STATE_DIR / "lifecycle.json"


class ShellState(str, Enum):
    WINDOWS_AUTHENTICATED = "windows-authenticated"
    HOST_BRIDGE_STARTING = "host-bridge-starting"
    LINUX_RUNTIME_STARTING = "linux-runtime-starting"
    COMPOSITOR_STARTING = "compositor-starting"
    DESKTOP_READY = "desktop-ready"
    SHELL_MODE = "shell-mode"
    RECOVERING = "recovering"
    WINDOWS_RECOVERY_SHELL = "windows-recovery-shell"


@dataclass(frozen=True)
class ShellTransition:
    source: ShellState
    target: ShellState
    reason: str
    timestamp: datetime


class NtKdeShellLifecycle:
    """Allow shell mode only after every readiness gate has passed."""

    def __init__(self, persist_path: Path | str | None = None) -> None:
        self.state = ShellState.WINDOWS_AUTHENTICATED
        self.failure_reason: str | None = None
        self.history: list[ShellTransition] = []
        self._persist_path: Path | None = (
            Path(persist_path) if persist_path is not None else None
        )

    def start_host_bridge(self) -> None:
        self._move(ShellState.WINDOWS_AUTHENTICATED, ShellState.HOST_BRIDGE_STARTING)

    def start_linux_runtime(self) -> None:
        self._move(ShellState.HOST_BRIDGE_STARTING, ShellState.LINUX_RUNTIME_STARTING)

    def start_compositor(self) -> None:
        self._move(ShellState.LINUX_RUNTIME_STARTING, ShellState.COMPOSITOR_STARTING)

    def mark_desktop_ready(self) -> None:
        self._move(ShellState.COMPOSITOR_STARTING, ShellState.DESKTOP_READY)

    def enter_shell_mode(self) -> None:
        self._move(ShellState.DESKTOP_READY, ShellState.SHELL_MODE)

    def fail(self, reason: str) -> None:
        if not reason:
            raise ProtocolError("shell failure requires a reason")
        self.failure_reason = reason
        self._record(ShellState.RECOVERING, reason)
        # Auto-persist on failure so crash diagnostics survive
        if self._persist_path:
            self.save(self._persist_path)

    def recover_windows_shell(self) -> None:
        if self.state is not ShellState.RECOVERING:
            raise ProtocolError("Windows recovery shell requires recovery state")
        self._record(ShellState.WINDOWS_RECOVERY_SHELL, "recovery shell activated")

    def retry(self) -> None:
        if self.state is not ShellState.WINDOWS_RECOVERY_SHELL:
            raise ProtocolError("retry requires the Windows recovery shell")
        self.failure_reason = None
        self._record(ShellState.WINDOWS_AUTHENTICATED, "retry requested")

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-safe lifecycle state for host diagnostics."""
        return {
            "state": self.state.value,
            "failure_reason": self.failure_reason,
            "history": [
                {
                    "source": transition.source.value,
                    "target": transition.target.value,
                    "reason": transition.reason,
                    "timestamp": transition.timestamp.isoformat(),
                }
                for transition in self.history
            ],
        }

    def save(self, path: Path | str | None = None) -> Path:
        """Persist the lifecycle snapshot to a JSON file.

        Args:
            path: File path to write. Defaults to the instance's persist_path,
                  or ~/.local/state/nt-plasma/lifecycle.json.

        Returns:
            The path that was written.
        """
        target = Path(path) if path else (self._persist_path or _DEFAULT_LIFECYCLE_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = self.snapshot()
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: Path | str | None = None) -> "NtKdeShellLifecycle":
        """Load a previously persisted lifecycle, appending its history.

        Args:
            path: File path to read. Defaults to the standard state path.

        Returns:
            A new NtKdeShellLifecycle with restored state and history.
        """
        target = Path(path) if path else _DEFAULT_LIFECYCLE_PATH
        instance = cls(persist_path=target)

        if not target.exists():
            return instance

        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            instance.state = ShellState(data["state"])
            instance.failure_reason = data.get("failure_reason")
            for entry in data.get("history", []):
                instance.history.append(
                    ShellTransition(
                        source=ShellState(entry["source"]),
                        target=ShellState(entry["target"]),
                        reason=entry["reason"],
                        timestamp=datetime.fromisoformat(entry["timestamp"]),
                    )
                )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file — start fresh but don't lose the file
            pass

        return instance

    def _move(self, expected: ShellState, target: ShellState) -> None:
        if self.state is not expected:
            raise ProtocolError(f"invalid shell transition: {self.state} -> {target}")
        self._record(target, "lifecycle transition")

    def _record(self, target: ShellState, reason: str) -> None:
        source = self.state
        self.state = target
        self.history.append(
            ShellTransition(source, target, reason, datetime.now(timezone.utc))
        )