import unittest
import asyncio
from gossipmesh.consensus.backoff import AdaptiveBackoffController
from gossipmesh.consensus.heartbeat import HeartbeatManager

class TestAdaptiveBackoffController(unittest.TestCase):
    def setUp(self):
        self.controller = AdaptiveBackoffController(base_interval=1.0, max_interval=16.0)

    def test_initial_backoff(self):
        self.assertEqual(self.controller.get_backoff_interval("node-1"), 1.0)

    def test_exponential_backoff_on_failures(self):
        node = "node-2"
        self.controller.record_failure(node)
        self.assertEqual(self.controller.get_backoff_interval(node), 1.0)
        self.controller.record_failure(node)
        self.assertEqual(self.controller.get_backoff_interval(node), 2.0)
        self.controller.record_failure(node)
        self.assertEqual(self.controller.get_backoff_interval(node), 4.0)

    def test_success_resets_failures(self):
        node = "node-3"
        self.controller.record_failure(node)
        self.controller.record_failure(node)
        self.assertEqual(self.controller.get_backoff_interval(node), 2.0)
        self.controller.record_success(node, 0.1)
        self.assertEqual(self.controller.get_backoff_interval(node), 1.0)

    def test_partition_detection(self):
        node = "node-4"
        self.assertFalse(self.controller.is_partitioned(node))
        for _ in range(3):
            self.controller.record_failure(node)
        self.assertTrue(self.controller.is_partitioned(node))

class TestHeartbeatManager(unittest.TestCase):
    def test_heartbeat_pulse_success(self):
        def mock_ping(peer_id):
            return True

        manager = HeartbeatManager(node_id="local", ping_callback=mock_ping)
        manager.register_peer("peer-1")
        
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(manager.pulse("peer-1"))
        self.assertTrue(res)
        self.assertEqual(manager.get_next_interval("peer-1"), 1.0)

    def test_heartbeat_pulse_failure(self):
        def mock_ping(peer_id):
            return False

        manager = HeartbeatManager(node_id="local", ping_callback=mock_ping)
        manager.register_peer("peer-1")
        
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(manager.pulse("peer-1"))
        self.assertFalse(res)
        self.controller = manager.controller
        self.assertEqual(manager.get_next_interval("peer-1"), 1.0)
        loop.run_until_complete(manager.pulse("peer-1"))
        self.assertEqual(manager.get_next_interval("peer-1"), 2.0)

if __name__ == "__main__":
    unittest.main()
