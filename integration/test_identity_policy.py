import unittest

from integration.bridge_protocol import ProtocolError
from integration.identity_policy import authorize_identity_request


class IdentityPolicyTests(unittest.TestCase):
    def test_authenticated_identity_request_is_allowed(self):
        self.assertEqual(authorize_identity_request("session-identity", True), "session-identity")

    def test_unauthenticated_or_unknown_request_is_rejected(self):
        with self.assertRaises(ProtocolError):
            authorize_identity_request("session-identity", False)
        with self.assertRaises(ProtocolError):
            authorize_identity_request("password-forwarding", True)


if __name__ == "__main__":
    unittest.main()