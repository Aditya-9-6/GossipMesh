import unittest
import time
from gossipmesh.p2p.transport import P2PSessionTransport
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator


class TestP2PTransport(unittest.TestCase):
    def test_transport_flow_and_rotation(self):
        alice_rotator = EphemeralSessionKeyRotator()
        bob_rotator = EphemeralSessionKeyRotator()

        transport_a = P2PSessionTransport(max_messages=5, max_time_seconds=60.0)
        transport_b = P2PSessionTransport(max_messages=5, max_time_seconds=60.0)

        transport_a.initialize_session(bob_rotator.get_public_bytes())
        transport_b.initialize_session(alice_rotator.get_public_bytes())

        # Send 5 messages to trigger automatic rotation condition
        for i in range(5):
            plaintext = f"msg {i}".encode()
            ct = transport_a.send_message(plaintext)
            # In real system, transport_b matches the session key state or rotates synchronously
            # Here we test message counter and rotation flag

        self.assertTrue(transport_a.should_rotate())


if __name__ == "__main__":
    unittest.main()
