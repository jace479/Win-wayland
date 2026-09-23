import unittest

from integration.bridge_policy import authorize_operation
from integration.bridge_protocol import ProtocolError


class OperationPolicyTests(unittest.TestCase):
    def test_normal_operation_needs_no_privilege(self):
        policy = authorize_operation("app.launch", privileged_capability=False)

        self.assertFalse(policy.privileged)

    def test_privileged_operation_requires_capability(self):
        with self.assertRaises(ProtocolError):
            authorize_operation("host.restart-bridge", privileged_capability=False)

        policy = authorize_operation("host.restart-bridge", privileged_capability=True)
        self.assertTrue(policy.privileged)

    def test_shell_forwarding_is_not_an_operation(self):
        with self.assertRaises(ProtocolError):
            authorize_operation("powershell.execute", privileged_capability=True)

        with self.assertRaises(ProtocolError):
            authorize_operation("bash.execute", privileged_capability=True)


if __name__ == "__main__":
    unittest.main()