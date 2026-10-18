import unittest
import asyncio
from gossipmesh.p2p.dht import KademliaDHT, DHTNode, KBucket
from gossipmesh.p2p.node import GossipNode, GossipTopic

class TestKademliaDHT(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_dht_node_creation(self):
        node = DHTNode("node_alpha", "127.0.0.1", 9001)
        self.assertEqual(node.node_id, "node_alpha")
        self.assertGreater(node.numeric_id, 0)
        d = node.to_dict()
        reconstructed = DHTNode.from_dict(d)
        self.assertEqual(node.node_id, reconstructed.node_id)

    def test_kbucket_operations(self):
        async def run():
            bucket = KBucket(0, 2**160, k=2)
            n1 = DHTNode("peer1", "127.0.0.1", 8001)
            n2 = DHTNode("peer2", "127.0.0.1", 8002)
            n3 = DHTNode("peer3", "127.0.0.1", 8003)

            self.assertTrue(await bucket.add_node(n1))
            self.assertTrue(await bucket.add_node(n2))
            # Full bucket should reject or handle
            res = await bucket.add_node(n3)
            nodes = await bucket.get_nodes()
            self.assertIn(n1, nodes)
            self.assertIn(n2, nodes)

            await bucket.remove_node("peer1")
            nodes_after = await bucket.get_nodes()
            self.assertEqual(len(nodes_after), 1)

        self.loop.run_until_complete(run())

    def test_kademlia_routing(self):
        async def run():
            local = DHTNode("local_node", "127.0.0.1", 8000)
            dht = KademliaDHT(local)

            p1 = DHTNode("peer_a", "127.0.0.1", 8001)
            p2 = DHTNode("peer_b", "127.0.0.1", 8002)

            await dht.add_node(p1)
            await dht.add_node(p2)

            stats = await dht.get_routing_table_stats()
            self.assertEqual(stats["total_peers"], 2)

            close_nodes = await dht.find_close_nodes("peer_a", count=1)
            self.assertEqual(len(close_nodes), 1)
            self.assertEqual(close_nodes[0].node_id, "peer_a")

        self.loop.run_until_complete(run())

    def test_gossip_node_dht_integration(self):
        async def run():
            gnode = GossipNode("agent_master", mesh_dir=".gossip_test_mesh")
            await gnode.discover_peer("agent_worker_1", "127.0.0.1", 8011)
            await gnode.discover_peer("agent_worker_2", "127.0.0.1", 8012)

            closest = await gnode.find_closest_peers("agent_worker_1")
            self.assertGreaterEqual(len(closest), 1)
            self.assertEqual(closest[0].node_id, "agent_worker_1")

        self.loop.run_until_complete(run())

if __name__ == "__main__":
    unittest.main()
