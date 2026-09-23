import unittest

from integration.bridge_protocol import ProtocolError
from integration.shell_lifecycle import NtKdeShellLifecycle, ShellState


class ShellLifecycleTests(unittest.TestCase):
    def test_shell_mode_requires_all_readiness_gates(self):
        lifecycle = NtKdeShellLifecycle()
        lifecycle.start_host_bridge()
        lifecycle.start_linux_runtime()
        lifecycle.start_compositor()
        lifecycle.mark_desktop_ready()
        lifecycle.enter_shell_mode()

        self.assertIs(lifecycle.state, ShellState.SHELL_MODE)

    def test_failure_recovers_without_losing_windows_authentication(self):
        lifecycle = NtKdeShellLifecycle()
        lifecycle.start_host_bridge()
        lifecycle.fail("compositor unavailable")
        lifecycle.recover_windows_shell()

        self.assertIs(lifecycle.state, ShellState.WINDOWS_RECOVERY_SHELL)
        self.assertEqual(lifecycle.failure_reason, "compositor unavailable")

        lifecycle.retry()
        self.assertIs(lifecycle.state, ShellState.WINDOWS_AUTHENTICATED)

    def test_shell_mode_cannot_be_entered_early(self):
        with self.assertRaises(ProtocolError):
            NtKdeShellLifecycle().enter_shell_mode()

    def test_failure_requires_reason(self):
        with self.assertRaises(ProtocolError):
            NtKdeShellLifecycle().fail("")

    def test_transition_history_records_recovery_reason_and_timestamps(self):
        lifecycle = NtKdeShellLifecycle()
        lifecycle.fail("WSLg compositor unavailable")
        lifecycle.recover_windows_shell()

        self.assertEqual(len(lifecycle.history), 2)
        self.assertEqual(lifecycle.history[0].target, ShellState.RECOVERING)
        self.assertEqual(lifecycle.history[0].reason, "WSLg compositor unavailable")
        self.assertIsNotNone(lifecycle.history[0].timestamp.tzinfo)
        self.assertEqual(lifecycle.history[1].target, ShellState.WINDOWS_RECOVERY_SHELL)

    def test_snapshot_is_json_safe(self):
        lifecycle = NtKdeShellLifecycle()
        lifecycle.start_host_bridge()
        snapshot = lifecycle.snapshot()

        self.assertEqual(snapshot["state"], "host-bridge-starting")
        self.assertEqual(snapshot["history"][0]["target"], "host-bridge-starting")
        self.assertIsInstance(snapshot["history"][0]["timestamp"], str)


if __name__ == "__main__":
    unittest.main()