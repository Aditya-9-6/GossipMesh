import unittest
import time
from gossipmesh.p2p.churn import EntropyChurnDefense
from gossipmesh.p2p.node import GossipNode, GossipMessage, GossipTopic

class TestEntropyChurnDefense(unittest.TestCase):
    def setUp(self):
        self.defense = EntropyChurnDefense(window_size=10, entropy_threshold=1.5, max_ticks_to_drop=3)

    def test_normal_entropy(self):
        peer_id = "node-honest"
        # Feed varied timestamps
        for i in range(10):
            self.defense.record_message(peer_id, float(i * 3.5))
        
        is_dropped = self.defense.evaluate_peer(peer_id)
        self.assertFalse(is_dropped)
        self.assertFalse(self.defense.is_quarantined(peer_id))

    def test_sybil_flooding_detection(self):
        peer_id = "node-sybil"
        # Feed identical repetitive metadata (zero variance / low entropy)
        for _ in range(10):
            self.defense.record_message(peer_id, 42.0)

        # Evaluate multiple ticks to trigger max_ticks_to_drop=3
        self.assertFalse(self.defense.evaluate_peer(peer_id))
        self.assertFalse(self.defense.evaluate_peer(peer_id))
        is_dropped = self.defense.evaluate_peer(peer_id)
        
        self.assertTrue(is_dropped)
        self.assertTrue(self.defense.is_quarantined(peer_id))

    def test_node_integration_with_churn(self):
        node = GossipNode(node_id="node-main", mesh_dir=".gossip_mesh/test_ledger")
        sybil_id = "node-attacker"

        # Send flood of identical messages simulating Sybil heartbeat attack
        for i in range(15):
            msg = GossipMessage(
                topic=GossipTopic.HEARTBEAT,
                origin_node=sybil_id,
                payload={"seq": i},
                timestamp=100.0 # Constant timestamp -> zero entropy
            )
            node.ingest_message(msg)

        self.assertTrue(node.churn_defense.is_quarantined(sybil_id))

        # Further messages from quarantined node should be rejected instantly
        late_msg = GossipMessage(
            topic=GossipTopic.HEARTBEAT,
            origin_node=sybil_id,
            payload={"seq": 999},
            timestamp=200.0
        )
        self.assertFalse(node.ingest_message(late_msg))

if __name__ == "__main__":
    unittest.main()
