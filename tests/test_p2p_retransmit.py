import unittest
from gossipmesh.p2p.retransmit import RetransmissionCache
from gossipmesh.p2p.protocol import GossipProtocolHandler


class TestRetransmissionCache(unittest.TestCase):
    def test_put_and_get(self):
        cache = RetransmissionCache(capacity=10, max_memory_bytes=1024 * 1024)
        success = cache.put("msg-1", {"data": "hello"})
        self.assertTrue(success)
        res = cache.get("msg-1")
        self.assertEqual(res, {"data": "hello"})

    def test_capacity_eviction(self):
        cache = RetransmissionCache(capacity=2, max_memory_bytes=1024 * 1024)
        cache.put("msg-1", {"data": 1})
        cache.put("msg-2", {"data": 2})
        cache.put("msg-3", {"data": 3})

        self.assertIsNone(cache.get("msg-1"))
        self.assertEqual(cache.get("msg-2"), {"data": 2})
        self.assertEqual(cache.get("msg-3"), {"data": 3})

    def test_backpressure_signaling(self):
        cache = RetransmissionCache(capacity=4, max_memory_bytes=1024 * 1024)
        self.assertFalse(cache.check_backpressure())
        cache.put("msg-1", {"data": 1})
        cache.put("msg-2", {"data": 2})
        cache.put("msg-3", {"data": 3})
        cache.put("msg-4", {"data": 4})
        self.assertTrue(cache.check_backpressure())

    def test_protocol_handler_integration(self):
        handler = GossipProtocolHandler(capacity=2, max_memory_bytes=1024 * 1024)
        handler.handle_broadcast("m1", {"test": True})
        self.assertEqual(handler.request_retransmit("m1"), {"test": True})
        self.assertFalse(handler.is_congested())
        handler.handle_broadcast("m2", {"test": True})
        handler.handle_broadcast("m3", {"test": True})
        self.assertTrue(handler.is_congested())


if __name__ == "__main__":
    unittest.main()
