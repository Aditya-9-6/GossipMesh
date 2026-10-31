"""
Unit tests for decentralized adaptive heartbeat backoff mechanism.
"""

from __future__ import annotations

import unittest

from gossipmesh.consensus.backoff import AdaptiveBackoffConfig, NodeHeartbackoffState
from gossipmesh.consensus.heartbeat import MeshHeartbeatManager


class TestConsensusBackoff(unittest.TestCase):
    def setUp(self):
        self.config = AdaptiveBackoffConfig(
            base_interval=1.0,
            min_interval=0.2,
            max_interval=10.0,
            backoff_factor=2.0,
            jitter_factor=0.0,
            partition_threshold_failures=3,
        )
        self.state = NodeHeartbackoffState(node_id="node-alpha", config=self.config)

    def test_initial_state(self):
        self.assertEqual(self.state.node_id, "node-alpha")
        self.assertEqual(self.state.get_current_interval(), 1.0)
        self.assertFalse(self.state.is_partitioned)
        self.assertEqual(self.state.consecutive_failures, 0)

    def test_record_success_resets_failures_and_adapts(self):
        self.state.record_failure()
        self.state.record_failure()
        self.assertEqual(self.state.consecutive_failures, 2)

        interval = self.state.record_success(latency=0.05)
        self.assertEqual(self.state.consecutive_failures, 0)
        self.assertFalse(self.state.is_partitioned)
        self.assertGreaterEqual(interval, self.config.min_interval)

    def test_exponential_backoff_and_partition_detection(self):
        # 1st failure
        i1 = self.state.record_failure()
        self.assertFalse(self.state.is_partitioned)
        self.assertEqual(i1, 2.0)

        # 2nd failure
        i2 = self.state.record_failure()
        self.assertFalse(self.state.is_partitioned)
        self.assertEqual(i2, 4.0)

        # 3rd failure triggers partition
        i3 = self.state.record_failure()
        self.assertTrue(self.state.is_partitioned)
        self.assertEqual(self.state.consecutive_failures, 3)
        self.assertEqual(i3, 8.0)

    def test_mesh_heartbeat_manager_integration(self):
        manager = MeshHeartbeatManager(config=self.config)

        # Simulate failures leading to partition
        manager.register_heartbeat_timeout("node-beta")
        manager.register_heartbeat_timeout("node-beta")
        manager.register_heartbeat_timeout("node-beta")

        self.assertTrue(manager.is_node_partitioned("node-beta"))
        self.assertIn("node-beta", manager.get_partitioned_nodes())

        # Simulate mesh healing (ack received)
        manager.register_heartbeat_ack("node-beta", latency=0.02)
        self.assertFalse(manager.is_node_partitioned("node-beta"))
        self.assertEqual(manager.get_partitioned_nodes(), [])


if __name__ == "__main અમારા__":
    unittest.main()
