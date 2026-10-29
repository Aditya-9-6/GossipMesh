import unittest
from gossipmesh.p2p.dht import KademliaDHT, xor_distance
from gossipmesh.p2p.node import PeerManager


class TestKademliaDHT(unittest.TestCase):
    def test_xor_distance(self):
        d = xor_distance("node1", "node1")
        self.assertEqual(d, 0)
        d2 = xor_distance("node1", "node2")
        self.assertGreater(d2, 0)

    def test_dht_routing_and_buckets(self):
        dht = KademliaDHT(local_node_id="local_node", k=5)
        for i in range(10):
            success = dht.add_node(f"node_{i}", f"127.0.0.1:800{i}")
            self.assertTrue(success)

        close_nodes = dht.find_close_nodes("target_node", count=5)
        self.assertEqual(len(close_nodes), 5)

        dht.remove_node("node_0")
        close_nodes_after = dht.find_close_nodes("target_node", count=10)
        node_ids = [n.node_id for n in close_nodes_after]
        self.assertNotIn("node_0", node_ids)

    def test_peer_manager_integration(self):
        manager = PeerManager(local_node_id="local_manager")
        manager.add_peer("peer_alpha", "192.168.1.10:5000")
        manager.add_peer("peer_beta", "192.168.1.11:5000")

        nearest = manager.find_nearest_peers("peer_target", count=2)
        self.assertEqual(len(nearest), 2)

        manager.remove_peer("peer_alpha")
        nearest_after = manager.find_nearest_peers("peer_target", count=2)
        self.assertEqual(len(nearest_after), 1)
        self.assertEqual(nearest_after[0].node_id, "peer_beta")


if __name__ == "__main__":
    unittest.main()
