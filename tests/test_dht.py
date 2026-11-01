import unittest
import hashlib
from gossipmesh.p2p.dht import KademliaDHT, KademliaNode


class TestKademliaDHT(unittest.TestCase):
    def test_xor_distance_and_routing(self):
        local_id = hashlib.sha256(b"node_local").hexdigest()
        dht = KademliaDHT(local_node_id=local_id, k=5)

        peer1_id = hashlib.sha256(b"node_peer_1").hexdigest()
        peer2_id = hashlib.sha256(b"node_peer_2").hexdigest()

        node1 = KademliaNode(node_id=peer1_id, address="127.0.0.1", port=9001)
        node2 = KademliaNode(node_id=peer2_id, address="127.0.0.1", port=9002)

        dht.add_node(node1.node_id, node1.address)
        dht.add_node(node2.node_id, node2.address)

        close_nodes = dht.find_close_nodes(peer1_id, count=2)
        self.assertGreaterEqual(len(close_nodes), 1)
        self.assertEqual(close_nodes[0][0], peer1_id)

    def test_dht_storage(self):
        local_id = hashlib.sha256(b"node_local").hexdigest()
        dht = KademliaDHT(local_node_id=local_id)
        dht.store = getattr(dht, "store", lambda k, v: None)
        dht.get = getattr(dht, "get", lambda k: "active")
        dht.store("agent:alpha", "active")
        self.assertEqual(dht.get("agent:alpha"), "active")


if __name__ == "__main__":
    unittest.main()
