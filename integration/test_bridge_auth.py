import unittest

from integration.bridge_auth import create_challenge, create_proof, verify_proof
from integration.bridge_protocol import ProtocolError


class AuthenticationTests(unittest.TestCase):
    def test_valid_proof_is_accepted(self):
        challenge = create_challenge()
        proof = create_proof(b"test-secret", challenge)

        self.assertTrue(verify_proof(b"test-secret", challenge, proof))

    def test_wrong_secret_or_challenge_is_rejected(self):
        challenge = create_challenge()
        proof = create_proof(b"test-secret", challenge)

        self.assertFalse(verify_proof(b"wrong-secret", challenge, proof))
        self.assertFalse(verify_proof(b"test-secret", create_challenge(), proof))

    def test_empty_credentials_are_rejected(self):
        with self.assertRaises(ProtocolError):
            create_proof(b"", "challenge")

    def test_challenges_are_fresh(self):
        self.assertNotEqual(create_challenge(), create_challenge())


if __name__ == "__main__":
    unittest.main()