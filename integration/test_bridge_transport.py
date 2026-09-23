import io
import unittest

from integration.bridge_protocol import Message, ProtocolError
from integration.bridge_transport import encode_message, read_message


class TransportTests(unittest.TestCase):
    def test_message_can_be_read_from_wire_format(self):
        message = Message(1, "event-1", "event", "bridge.ping", {})

        self.assertEqual(read_message(io.BytesIO(encode_message(message))), message)

    def test_invalid_json_is_rejected(self):
        with self.assertRaises(ProtocolError):
            read_message(io.BytesIO(b"not-json\n"))

    def test_unterminated_message_is_rejected(self):
        with self.assertRaises(ProtocolError):
            read_message(io.BytesIO(b'{"version":1}'))


if __name__ == "__main__":
    unittest.main()