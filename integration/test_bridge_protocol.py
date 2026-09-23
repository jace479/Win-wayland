import unittest

from integration.bridge_protocol import (
    Message,
    ProtocolError,
    negotiate_capabilities,
    validate_application_request,
)


class MessageTests(unittest.TestCase):
    def test_message_round_trip(self):
        message = Message(1, "request-1", "request", "hello", {"name": "desktop"})

        self.assertEqual(Message.from_dict(message.to_dict()), message)

    def test_missing_field_is_rejected(self):
        with self.assertRaises(ProtocolError):
            Message.from_dict({"version": 1, "id": "1"})

    def test_unknown_version_is_rejected(self):
        with self.assertRaises(ProtocolError):
            Message(99, "request-1", "request", "hello", {})


class NegotiationTests(unittest.TestCase):
    def test_only_shared_capabilities_are_enabled(self):
        result = negotiate_capabilities(
            {"capabilities": ["app-launch", "clipboard"]},
            {"capabilities": ["app-launch", "windows"]},
        )

        self.assertEqual(result, {"version": 1, "capabilities": ["app-launch"]})

    def test_unlisted_application_is_rejected(self):
        with self.assertRaises(ProtocolError):
            validate_application_request(
                {"application": "arbitrary-executable"},
                {"notepad": "notepad.exe"},
            )


if __name__ == "__main__":
    unittest.main()