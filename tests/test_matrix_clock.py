import unittest
import time
from gossipmesh.p2p.matrix_clock import MatrixClock, BoundedMatrixClockReconstructionEngine


class TestMatrixClockAndEngine(unittest.TestCase):

    def test_matrix_clock_basic(self):
        mc = MatrixClock("node_A", ["node_A", "node_B"])
        self.assertEqual(mc.increment(), {"node_A": 1})
        
        mc.update("node_B", {"node_A": 1, "node_B": 2})
        snapshot = mc.snapshot()
        self.assertIn("node_A", snapshot)
        self.assertIn("node_B", snapshot)
        self.assertEqual(snapshot["node_B"]["node_B"], 2)

    def test_engine_in_order_delivery(self):
        engine = BoundedMatrixClockReconstructionEngine("node_A", max_buffer_size=10)
        
        # Node B sends message 1
        delivered = engine.ingest_payload("node_B", {"node_B": 1}, "payload_1")
        self.assertEqual(delivered, ["payload_1"])
        self.assertEqual(engine.buffer_size(), 0)

    def test_engine_out_of_order_buffering(self):
        engine = BoundedMatrixClockReconstructionEngine("node_A", max_buffer_size=10)
        
        # Node B sends message 2 before message 1 (causal gap)
        delivered = engine.ingest_payload("node_B", {"node_B": 2}, "payload_2")
        self.assertEqual(delivered, [])
        self.assertEqual(engine.buffer_size(), 1)
        
        # Now send message 1, which should unlock both 1 and 2
        delivered_now = engine.ingest_payload("node_B", {"node_B": 1}, "payload_1")
        self.assertIn("payload_1", delivered_now)
        self.assertIn("payload_2", delivered_now)
        self.assertEqual(engine.buffer_size(), 0)

    def test_engine_stale_state_pruning(self):
        # Very short stale window of 0.1 seconds
        engine = BoundedMatrixClockReconstructionEngine("node_A", max_buffer_size=10, max_stale_window_sec=0.1)
        
        # Ingest out-of-order message
        delivered = engine.ingest_payload("node_B", {"node_B": 5}, "stale_payload")
        self.assertEqual(delivered, [])
        self.assertEqual(engine.buffer_size(), 1)
        
        # Wait for stale window to elapse
        time.sleep(0.15)
        
        # Ingest another message, triggering prune
        delivered2 = engine.ingest_payload("node_C", {"node_C": 1}, "fresh_payload")
        self.assertIn("fresh_payload", delivered2)
        # Stale payload should have been dropped
        self.assertEqual(engine.buffer_size(), 0)

    def test_buffer_capacity_eviction(self):
        engine = BoundedMatrixClockReconstructionEngine("node_A", max_buffer_size=2)
        
        # Fill buffer beyond capacity
        engine.ingest_payload("node_B", {"node_B": 10}, "p1")
        engine.ingest_payload("node_B", {"node_B": 11}, "p2")
        self.assertEqual(engine.buffer_size(), 2)
        
        # Adding third should evict oldest (p1)
        engine.ingest_payload("node_B", {"node_B": 12}, "p3")
        self.assertEqual(engine.buffer_size(), 2)


if __name__ == "__main__":
    unittest.main()
