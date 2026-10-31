import unittest
from gossipmesh.p2p.dht import KademliaDHT, xor_distance, id_to_int
from gossipmesh.p2p.node import PeerManager


class TestKademliaDHT(unittest.TestCase):
    def test_xor_distance(self):
        id1 = "0000000000000000000000000000000000000001"
        id2 = "0000000000000000000000000000000000000003"
        dist = xor_distance(id1, id2)
        self.assertEqual(dist, 2)

    def test_dht_routing_and_closest_nodes(self):
        local_id = "0000000000000000000000000000000000000000"
        dht = KademliaDHT(local_node_id=local_id, k=5)

        dht.add_node("0000000000000000000000000000000000000001", "127.0.0.1:8001")
        dht.add_node("000000000000000000000000000000000000000f", "127.0.0.1:8002")
        dht.add_node("ffffffffffffffffffffffffffffffffffffffff", "127.0.0.1:8003")

        closest = dht.find_close_nodes("0000000000000000000000000000000000000002", count=2)
        self.assertEqual(len(closest), 2)
        # Node 1 (dist 3) and Node f (dist d) should be closer than ffff... (dist large)
        self.assertEqual(closest[0][0], "0000000000000000000000000000000000000001")

    def test_peer_manager_dht_integration(self):
        manager = PeerManager(local_node_id="node_local")
        manager.add_peer("node_alpha", "127.0.0.1:9001")
        manager.add_peer("node_beta", "127.0.0.1:9002")

        closest = manager.find_closest_peers("node_target", count=5)
        self.assertEqual(len(closest), 2)
        manager.remove_peer("node_alpha")
        self.assertEqual(len(manager.find_closest_peers("node_target", count=5)), 1)


if __name__ == "__main最多的":
    unittest.main()
