"""
Unit tests for decentralized adaptive heartbeat backoff mechanism.
"""

import unittest
from gossipmesh.consensus.backoff import AdaptiveBackoffCalculator
from gossipmesh.consensus.heartbeat import AdaptiveHeartbeatManager, NodeHeartbeatState


class TestConsensusBackoff(unittest.TestCase):

    def setUp(self):
        self.calculator = AdaptiveBackoffCalculator(
            base_interval=1.0,
            min_interval=0.2,
            max_interval=10.0,
            backoff_multiplier=2.0,
        )
        self.manager = AdaptiveHeartbeatManager(
            calculator=self.calculator,
            partition_failure_threshold=3,
        )

    def test_normal_operation_latency(self):
        node_id = "node-alpha"
        # Record some fast ACKs
        self.manager.record_ack_received(node_id, 0.05)
        self.manager.record_ack_received(node_id, 0.07)

        interval = self.manager.get_next_interval(node_id)
        self.assertGreaterEqual(interval, 0.2)
        self.assertLessEqual(interval, 1.0)

    def test_exponential_backoff_on_failures(self):
        node_id = "node-beta"
        # 1 failure
        self.manager.record_timeout(node_id)
        interval_1 = self.manager.get_next_interval(node_id)
        self.assertEqual(interval_1, 2.0)

        # 2 failures
        self.manager.record_timeout(node_id)
        interval_2 = self.manager.get_next_interval(node_id)
        self.assertEqual(interval_2, 4.0)

    def test_partition_detection_and_flooding_prevention(self):
        node_id = "node-gamma"
        # Trigger partition threshold (3 failures)
        for _ in range(3):
            self.manager.record_timeout(node_id)

        state = self.manager.get_or_create_state(node_id)
        self.assertTrue(state.is_partitioned)

        # Interval should clamp to max_interval to prevent flooding
        interval = self.manager.get_next_interval(node_id)
        self.assertEqual(interval, 10.0)

    def test_mesh_healing_convergence(self):
        node_id = "node-delta"
        for _ in range(3):
            self.manager.record_timeout(node_id)

        self.assertTrue(self.manager.get_or_create_state(node_id).is_partitioned)

        # Mesh healing event
        healed = self.manager.check_mesh_healing(node_id)
        self.assertTrue(healed)

        state = self.manager.get_or_create_state(node_id)
        self.assertFalse(state.is_partitioned)
        self.assertEqual(state.consecutive_failures, 0)

        # Post-healing interval should be normal
        interval = self.manager.get_next_interval(node_id)
        self.assertLessEqual(interval, 1.0)


if __name__ == "__main__":
    unittest.main()
