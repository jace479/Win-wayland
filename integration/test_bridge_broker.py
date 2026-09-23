import unittest

from integration.bridge_broker import HostBroker
from integration.bridge_protocol import Message, ProtocolError
from integration.bridge_session import BridgeSession
from integration.app_catalog import ApplicationCatalog, ApplicationEntry


def ready_session() -> BridgeSession:
    session = BridgeSession()
    session.connect()
    session.authenticate()
    session.mark_ready()
    return session


class HostBrokerTests(unittest.TestCase):
    def setUp(self):
        self.broker = HostBroker(ready_session(), {"notepad": "notepad.exe"})

    def test_allow_listed_application_is_accepted(self):
        result = self.broker.dispatch(
            Message(1, "1", "request", "app.launch", {"application": "notepad"})
        )

        self.assertEqual(result.payload["executable"], "notepad.exe")

    def test_unknown_application_is_rejected(self):
        with self.assertRaises(ProtocolError):
            self.broker.dispatch(
                Message(1, "1", "request", "app.launch", {"application": "cmd"})
            )

    def test_application_list_is_projected_without_executable_paths(self):
        result = self.broker.dispatch(Message(1, "1", "request", "app.list", {}))

        self.assertEqual(
            result.payload,
            {
                "applications": [
                    {
                        "id": "notepad",
                        "name": "notepad",
                        "category": "Other",
                        "origin": "windows",
                        "arguments": [],
                    }
                ]
            },
        )

    def test_application_list_can_combine_linux_and_windows_entries(self):
        catalog = ApplicationCatalog(
            (ApplicationEntry("kate", "Kate", "/usr/bin/kate", origin="linux"),)
        )
        catalog.merge(
            (ApplicationEntry("notepad", "Notepad", "notepad.exe", origin="windows"),)
        )
        broker = HostBroker(ready_session(), {"notepad": "notepad.exe"}, desktop_catalog=catalog)

        result = broker.dispatch(Message(1, "1", "request", "app.list", {}))

        self.assertEqual(
            [(item["id"], item["origin"]) for item in result.payload["applications"]],
            [("kate", "linux"), ("notepad", "windows")],
        )
        self.assertNotIn("/usr/bin/kate", result.payload["applications"][0].values())
        self.assertNotIn("notepad.exe", result.payload["applications"][1].values())

    def test_identity_returns_metadata_without_credentials(self):
        result = self.broker.dispatch(
            Message(1, "1", "request", "identity.session", {})
        )

        self.assertEqual(result.payload, {"identity": "Windows user"})
        self.assertNotIn("password", result.payload)
        self.assertNotIn("token", result.payload)

    def test_sso_returns_approval_not_a_secret(self):
        result = self.broker.dispatch(
            Message(1, "1", "request", "identity.sso-request", {})
        )

        self.assertEqual(result.payload["request"], "approved-by-host")
        self.assertNotIn("password", result.payload)
        self.assertNotIn("token", result.payload)

    def test_broker_requires_ready_session(self):
        broker = HostBroker(BridgeSession(), {})

        with self.assertRaises(ProtocolError):
            broker.dispatch(Message(1, "1", "request", "app.launch", {}))

    def test_privileged_request_requires_capability(self):
        message = Message(1, "1", "request", "host.restart-bridge", {})

        with self.assertRaises(ProtocolError):
            self.broker.dispatch(message)
        result = self.broker.dispatch(message, privileged_capability=True)
        self.assertEqual(result.operation, "host.restart-bridge.accepted")

    def test_event_is_not_accepted_as_a_request(self):
        with self.assertRaises(ProtocolError):
            self.broker.dispatch(Message(1, "1", "event", "app.launch", {}))


if __name__ == "__main__":
    unittest.main()