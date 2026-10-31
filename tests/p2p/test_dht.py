import unittest
from gossipmesh.p2p.dht import KademliaDHT, KademliaNode, xor_distance


class TestDHT(unittest.TestCase):
    def test_xor_distance(self):
        id1 = "0000000000000000000000000000000000000001"
        id2 = "0000000000000000000000000000000000000003"
        self.assertEqual(xor_distance(id1, id2), 2)

    def test_kademlia_routing(self):
        local_node = KademliaNode("0" * 40, "127.0.0.1", 8000)
        dht = KademliaDHT(local_node, k=20)

        node1 = KademliaNode("0" * 39 + "1", "127.0.0.1", 8001)
        node2 = KademliaNode("0" * 39 + "2", "127.0.0.1", 8002)

        dht.add_node(node1)
        dht.add_node(node2)

        closest = dht.find_closest_nodes("0" * 40, count=2)
        self.assertEqual(len(closest), 2)
        self.assertIn(node1, closest)
        self.assertIn(node2, closest)

    def test_peer_manager_integration(self):
        local_node = KademliaNode("a" * 40, "127.0.0.1", 9000)
        dht = KademliaDHT(local_node)
        node = KademliaNode("b" * 40, "127.0.0.1", 9001)
        dht.add_node(node)
        self.assertEqual(len(dht.get_all_nodes()), 1)


if __name__ == "__main__":
    unittest.main()
