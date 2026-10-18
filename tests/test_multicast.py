import unittest
import asyncio
from gossipmesh.p2p.multicast import PlumTreeMulticast, BoundedLRUCache
from gossipmesh.p2p.transport import P2PTransport

class TestBoundedLRUCache(unittest.TestCase):
    def test_cache_capacity(self):
        cache = BoundedLRUCache(capacity=2)
        cache.add("msg1")
        cache.add("msg2")
        self.assertIn("msg1", cache)
        self.assertIn("msg2", cache)
        
        cache.add("msg3")
        self.assertNotIn("msg1", cache)
        self.assertIn("msg3", cache)

class TestPlumTreeMulticast(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.multicast = PlumTreeMulticast("node-A")

    def tearDown(self):
        self.loop.close()

    def test_peer_management(self):
        async def run():
            await self.multicast.add_peer("node-B", eager=True)
            self.assertIn("node-B", self.multicast.eager_peers)
            
            await self.multicast.add_peer(
                "node-B", eager=False
            )
            self.assertNotIn("node-B", self.multicast.eager_peers)
            self.assertIn("node-B", self.multicast.lazy_peers)
            
            await self.multicast.remove_peer("node-B")
            self.assertNotIn("node-B", self.multicast.lazy_peers)

        self.loop.run_until_complete(run())

    def test_message_handling_and_pruning(self):
        async def run():
            await self.multicast.add_peer("node-B", eager=True)
            await self.multicast.add_peer("node-C", eager=False)
            
            res1 = await self.multicast.handle_message("msg-1", "node-B")
            self.assertEqual(res1["action"], "deliver")
            self.assertIn("node-C", res1["notify_lazy"])
            
            res2 = await self.multicast.handle_message("msg-1", "node-B")
            self.assertEqual(res2["action"], "prune")
            self.assertIn("node-B", self.multicast.lazy_peers)

        self.loop.run_until_complete(run())

    def test_graft(self):
        async def run():
            await self.multicast.add_peer("node-B", eager=False)
            await self.multicast.graft("node-B")
            self.assertIn("node-B", self.multicast.eager_peers)
            self.assertNotIn("node-B", self.multicast.lazy_peers)

        self.loop.run_until_complete(run())

class TestP2PTransport(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.transport = P2PTransport("node-A")

    def tearDown(self):
        self.loop.close()

    def test_transport_integration(self):
        async def run():
            await self.transport.register_peer("node-B", eager=True)
            await self.transport.receive_message("msg-100", "node-B", {"data": "test"})
            await self.transport.request_graft("node-B")
            self.assertIn("node-B", self.transport.multicast.eager_peers)

        self.loop.run_until_complete(run())

if __name__ == "__main__":
    unittest.main()
