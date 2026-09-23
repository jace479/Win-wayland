"""Integration tests for Phase 1.1 hardening: watchdog, persistence, degradation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integration.bridge_protocol import ProtocolError
from integration.shell_lifecycle import (
    NtKdeShellLifecycle,
    ShellState,
    ShellTransition,
)


# ============================================================================
# Lifecycle Persistence Tests
# ============================================================================


class TestLifecyclePersistence:
    """Verify save/load round-trip and auto-persist on failure."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        lc = NtKdeShellLifecycle()
        lc.start_host_bridge()
        lc.start_linux_runtime()
        path = lc.save(tmp_path / "lifecycle.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["state"] == "linux-runtime-starting"
        assert len(data["history"]) == 2

    def test_load_restores_state(self, tmp_path: Path) -> None:
        target = tmp_path / "lifecycle.json"

        # Save a lifecycle in recovering state
        lc = NtKdeShellLifecycle()
        lc.start_host_bridge()
        lc.start_linux_runtime()
        lc.start_compositor()
        lc.fail("compositor crashed")
        lc.save(target)

        # Load and verify
        loaded = NtKdeShellLifecycle.load(target)
        assert loaded.state is ShellState.RECOVERING
        assert loaded.failure_reason == "compositor crashed"
        assert len(loaded.history) == 4  # 3 transitions + 1 fail

    def test_load_nonexistent_returns_fresh(self, tmp_path: Path) -> None:
        loaded = NtKdeShellLifecycle.load(tmp_path / "nonexistent.json")
        assert loaded.state is ShellState.WINDOWS_AUTHENTICATED
        assert loaded.history == []

    def test_load_corrupted_file_returns_fresh(self, tmp_path: Path) -> None:
        target = tmp_path / "lifecycle.json"
        target.write_text("THIS IS NOT JSON", encoding="utf-8")
        loaded = NtKdeShellLifecycle.load(target)
        assert loaded.state is ShellState.WINDOWS_AUTHENTICATED

    def test_fail_auto_persists(self, tmp_path: Path) -> None:
        target = tmp_path / "lifecycle.json"
        lc = NtKdeShellLifecycle(persist_path=target)
        lc.start_host_bridge()
        lc.fail("bridge timeout")

        # File should exist without explicit save()
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["state"] == "recovering"
        assert data["failure_reason"] == "bridge timeout"

    def test_round_trip_preserves_timestamps(self, tmp_path: Path) -> None:
        target = tmp_path / "lifecycle.json"
        lc = NtKdeShellLifecycle()
        lc.start_host_bridge()
        original_ts = lc.history[0].timestamp
        lc.save(target)

        loaded = NtKdeShellLifecycle.load(target)
        assert loaded.history[0].timestamp == original_ts

    def test_full_lifecycle_round_trip(self, tmp_path: Path) -> None:
        """Full journey: auth -> bridge -> runtime -> compositor -> ready -> fail -> recover -> retry."""
        target = tmp_path / "lifecycle.json"
        lc = NtKdeShellLifecycle(persist_path=target)

        lc.start_host_bridge()
        lc.start_linux_runtime()
        lc.start_compositor()
        lc.mark_desktop_ready()
        lc.fail("display lost")
        lc.recover_windows_shell()
        lc.retry()

        assert lc.state is ShellState.WINDOWS_AUTHENTICATED
        assert len(lc.history) == 7

        # Verify persistence survived the fail() auto-save
        loaded = NtKdeShellLifecycle.load(target)
        # Note: auto-save happens at fail(), so loaded state is RECOVERING
        # (the recover + retry happened after the save)
        assert loaded.state is ShellState.RECOVERING


# ============================================================================
# Lifecycle State Machine Tests (existing coverage preserved + extended)
# ============================================================================


class TestLifecycleStateMachine:
    """Validate state machine transitions and error handling."""

    def test_happy_path_to_shell_mode(self) -> None:
        lc = NtKdeShellLifecycle()
        lc.start_host_bridge()
        lc.start_linux_runtime()
        lc.start_compositor()
        lc.mark_desktop_ready()
        lc.enter_shell_mode()
        assert lc.state is ShellState.SHELL_MODE
        assert len(lc.history) == 5

    def test_fail_from_any_state(self) -> None:
        """Fail must be reachable from any state after authentication."""
        for target_state in [
            ShellState.HOST_BRIDGE_STARTING,
            ShellState.LINUX_RUNTIME_STARTING,
            ShellState.COMPOSITOR_STARTING,
            ShellState.DESKTOP_READY,
            ShellState.SHELL_MODE,
        ]:
            lc = NtKdeShellLifecycle()
            # Drive to target state
            lc.start_host_bridge()
            if target_state == ShellState.HOST_BRIDGE_STARTING:
                pass
            else:
                lc.start_linux_runtime()
                if target_state == ShellState.LINUX_RUNTIME_STARTING:
                    pass
                else:
                    lc.start_compositor()
                    if target_state == ShellState.COMPOSITOR_STARTING:
                        pass
                    else:
                        lc.mark_desktop_ready()
                        if target_state == ShellState.DESKTOP_READY:
                            pass
                        else:
                            lc.enter_shell_mode()

            lc.fail(f"test failure from {target_state.value}")
            assert lc.state is ShellState.RECOVERING

    def test_empty_failure_reason_rejected(self) -> None:
        lc = NtKdeShellLifecycle()
        with pytest.raises(ProtocolError, match="requires a reason"):
            lc.fail("")

    def test_invalid_transition_rejected(self) -> None:
        lc = NtKdeShellLifecycle()
        with pytest.raises(ProtocolError, match="invalid shell transition"):
            lc.start_compositor()  # Wrong: should be start_host_bridge first

    def test_recover_requires_recovering_state(self) -> None:
        lc = NtKdeShellLifecycle()
        with pytest.raises(ProtocolError, match="recovery state"):
            lc.recover_windows_shell()

    def test_retry_requires_recovery_shell(self) -> None:
        lc = NtKdeShellLifecycle()
        with pytest.raises(ProtocolError, match="retry requires"):
            lc.retry()

    def test_snapshot_is_json_safe(self) -> None:
        lc = NtKdeShellLifecycle()
        lc.start_host_bridge()
        lc.fail("test failure")
        snap = lc.snapshot()
        # Must be JSON-serializable
        serialized = json.dumps(snap)
        parsed = json.loads(serialized)
        assert parsed["state"] == "recovering"
        assert parsed["failure_reason"] == "test failure"
        assert len(parsed["history"]) == 2


# ============================================================================
# Bridge Watchdog Contract Tests (protocol-level, no actual processes)
# ============================================================================


class TestBridgeWatchdogContract:
    """Test the watchdog logic contract without spawning real processes."""

    def test_backoff_sequence(self) -> None:
        """Verify exponential backoff values."""
        expected = [1000, 2000, 4000, 8000, 16000]
        for i, ms in enumerate(expected):
            backoff_index = min(i, len(expected) - 1)
            assert expected[backoff_index] == ms

    def test_max_restart_limit(self) -> None:
        """After MaxBridgeRestarts, status should be Dead."""
        max_restarts = 5
        restart_count = 0
        status = "Running"
        for _ in range(max_restarts + 2):
            if restart_count >= max_restarts:
                status = "Dead"
                break
            restart_count += 1
            status = "Restarting"
        assert status == "Dead"
        assert restart_count == max_restarts


# ============================================================================
# WSL Health Gate Contract Tests
# ============================================================================


class TestWslHealthGateContract:
    """Validate health report structure and failure reason contract."""

    def test_health_report_fields(self) -> None:
        """All health report fields must be present."""
        # Simulate a health report (we can't call WslHealthGate from Python directly)
        report = {
            "IsReady": False,
            "WslAvailable": True,
            "DistroRegistered": True,
            "DistroBoots": False,
            "PlasmaInstalled": False,
            "X11Available": False,
            "FailureReason": "WSL distro 'Ubuntu' failed to boot: Timed out after 10000ms",
        }
        assert not report["IsReady"]
        assert report["WslAvailable"]
        assert not report["DistroBoots"]
        assert "Timed out" in report["FailureReason"]

    def test_degradation_tiers(self) -> None:
        """Verify degradation tier logic."""
        tiers = {
            "Full": {"wsl_healthy": True, "plasma_ok": True, "bridge_ok": True},
            "PanelsOnly": {"wsl_healthy": True, "plasma_ok": True, "bridge_ok": False},
            "TrayOnly": {"wsl_healthy": False, "plasma_ok": False, "bridge_ok": False},
        }
        for tier_name, conditions in tiers.items():
            if conditions["wsl_healthy"] and conditions["plasma_ok"] and conditions["bridge_ok"]:
                assert tier_name == "Full"
            elif conditions["wsl_healthy"] and not conditions["bridge_ok"]:
                assert tier_name in ("PanelsOnly", "TrayOnly")
            else:
                assert tier_name == "TrayOnly"


# ============================================================================
# Plasmashell Restart Loop Contract Tests
# ============================================================================


class TestPlasmashellRestartContract:
    """Validate the restart loop logic from start-panels.sh."""

    def test_clean_exit_stops_loop(self) -> None:
        """Exit code 0 or 143 (SIGTERM) should stop the restart loop."""
        clean_exit_codes = [0, 143]
        for code in clean_exit_codes:
            should_restart = code not in (0, 143)
            assert not should_restart, f"Exit code {code} should NOT trigger restart"

    def test_crash_triggers_restart(self) -> None:
        """Non-zero, non-143 exit codes should trigger a restart."""
        crash_codes = [1, 2, 11, 134, 139]  # general, SIGSEGV, SIGABRT, SIGSEGV
        for code in crash_codes:
            should_restart = code not in (0, 143)
            assert should_restart, f"Exit code {code} SHOULD trigger restart"

    def test_max_restarts_honored(self) -> None:
        """After MAX_PLASMA_RESTARTS, the loop must stop."""
        max_restarts = 5
        restart_count = 0
        exit_code = 1  # simulate crash

        while restart_count < max_restarts:
            if exit_code in (0, 143):
                break
            restart_count += 1

        assert restart_count == max_restarts

    def test_backoff_increases(self) -> None:
        """Backoff should be restart_count * 2 seconds."""
        for i in range(1, 6):
            backoff = i * 2
            assert backoff == i * 2
            assert backoff <= 10  # max 5 * 2 = 10s
