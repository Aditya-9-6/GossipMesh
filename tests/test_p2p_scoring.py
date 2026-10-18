import unittest
from gossipmesh.p2p.scoring import PeerScore, ScoringRegistry
from gossipmesh.p2p.transport import P2PTransport

class TestPeerScoring(unittest.TestCase):
    def test_initial_score(self):
        score = PeerScore("node-1")
        self.assertEqual(score.compute_score(), 1.0)
        self.assertFalse(score.blacklisted)

    def test_valid_interactions(self):
        score = PeerScore("node-1")
        score.record_interaction(0.1, True)
        score.record_interaction(0.2, True)
        self.assertGreaterEqual(score.compute_score(), 0.7)
        self.assertFalse(score.blacklisted)

    def test_dynamic_blacklisting(self):
        registry = ScoringRegistry(reputation_threshold=0.5)
        node_id = "bad-node"
        for _ in range(10):
            registry.record(node_id, 0.5, False, protocol_error=True)
            
        self.assertTrue(registry.is_blacklisted(node_id))

    def test_transport_routing(self):
        transport = P2PTransport("local-node")
        peer_id = "peer-2"
        
        # Good message
        allowed = transport.receive_message(peer_id, {"data": "test"}, 0.1, True)
        self.assertTrue(allowed)
        
        # Spam / invalid messages to trigger blacklisting
        for _ in range(20):
            transport.receive_message(peer_id, {"data": "bad"}, 2.0, False, protocol_error=True)
            
        # Now should be blacklisted and rejected
        allowed_after = transport.send_message(peer_id, {"data": "test"})
        self.assertFalse(allowed_after)

if __name__ == "__main":
    unittest.main()
