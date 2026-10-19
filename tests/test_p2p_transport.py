import unittest
import time
from gossipmesh.p2p.transport import AdaptiveTransport, P2PSessionTransport
from gossipmesh.p2p.node import P2PNodeExtension
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator

class TestAdaptiveTransport(unittest.TestCase):
    def setUp(self):
        self.transport = AdaptiveTransport(base_fanout=3, target_prob=0.99, max_rtt_threshold=1.0)

    def test_record_and_prune(self):
        self.transport.record_metric("peer-fast", rtt=0.05, velocity=10.0)
        self.transport.record_metric("peer-slow", rtt=1.5, velocity=0.5)
        
        peers = ["peer-fast", "peer-slow", "peer-normal"]
        selected = self.transport.select_optimal_peers(peers, count=2)
        
        self.assertIn("peer-fast", selected)
        self.assertNotIn("peer-slow", selected)

    def test_adaptive_fanout_bounds(self):
        fanout = self.transport.compute_adaptive_fanout(10)
        self.assertGreaterEqual(fanout, 1)
        self.assertLessEqual(fanout, 10)

    def test_node_extension(self):
        node = P2PNodeExtension(node_id="node-1", base_fanout=2)
        node.record_peer_feedback("peer-a", 0.1, 5.0)
        targets = node.select_targets(["peer-a", "peer-b"])
        self.assertIsInstance(targets, list)


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
