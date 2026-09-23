import unittest

from integration.bridge_protocol import ProtocolError
from integration.bridge_session import BridgeSession, SessionState


class BridgeSessionTests(unittest.TestCase):
    def test_normal_startup_reaches_ready(self):
        session = BridgeSession()

        session.connect()
        session.authenticate()
        session.mark_ready()

        self.assertIs(session.state, SessionState.READY)
        session.require_ready()

    def test_startup_order_is_enforced(self):
        session = BridgeSession()

        with self.assertRaises(ProtocolError):
            session.mark_ready()

    def test_disconnect_enters_recovery_and_can_reconnect(self):
        session = BridgeSession()
        session.connect()
        session.authenticate()
        session.mark_ready()

        session.disconnect()
        self.assertIs(session.state, SessionState.RECOVERING)
        with self.assertRaises(ProtocolError):
            session.require_ready()

        session.recover()
        session.connect()
        session.authenticate()
        session.mark_ready()
        self.assertIs(session.state, SessionState.READY)

    def test_stopped_session_cannot_restart(self):
        session = BridgeSession()
        session.stop()

        with self.assertRaises(ProtocolError):
            session.connect()


if __name__ == "__main__":
    unittest.main()