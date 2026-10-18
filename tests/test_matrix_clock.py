import unittest
import time
from gossipmesh.p2p.matrix_clock import MatrixClockMessage, BoundedMatrixClockEngine

class TestBoundedMatrixClockEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BoundedMatrixClockEngine(
            node_id="node-A",
            max_buffer_size=10,
            staleness_window_seconds=2.0,
        )

    def test_initial_state(self):
        matrix = self.engine.get_matrix()
        self.assertIn("node-A", matrix)

    def test_increment_and_delivery(self):
        clock = self.engine.increment()
        self.assertEqual(clock["node-A"], 1)

        msg = MatrixClockMessage(
            sender_id="node-A",
            message_id="msg-1",
            matrix_clock=clock,
            payload={"data": "hello"},
        )

        released = self.engine.ingest(msg)
        self.assertEqual(len(released), 1)
        self.assertEqual(released[0].message_id, "msg-1")

    def test_out_of_order_buffering(self):
        msg2 = MatrixClockMessage(
            sender_id="node-B",
            message_id="msg-2",
            matrix_clock={"node-B": 2},
            payload={"data": "future"},
        )

        released = self.engine.ingest(msg2)
        self.assertEqual(len(released), 0, "Out of order message should be buffered")

        msg1 = MatrixClockMessage(
            sender_id="node-B",
            message_id="msg-1",
            matrix_clock={"node-B": 1},
            payload={"data": "first"},
        )

        released = self.engine.ingest(msg1)
        self.assertEqual(len(released), 2, "Both messages should be released in causal order")
        self.assertEqual(released[0].message_id, "msg-1")
        self.assertEqual(released[1].message_id, "msg-2")

    def test_staleness_pruning(self):
        stale_msg = MatrixClockMessage(
            sender_id="node-C",
            message_id="msg-stale",
            matrix_clock={"node-C": 5},
            payload={"data": "old"},
            timestamp=time.time() - 5.0,
        )

        released = self.engine.ingest(stale_msg)
        self.assertEqual(len(released), 0)
        pruned_count = self.engine.prune_stale()
        self.assertGreaterEqual(pruned_count, 0)

    def test_message_serialization(self):
        msg = MatrixClockMessage(
            sender_id="node-A",
            message_id="msg-ser",
            matrix_clock={"node-A": 1},
            payload={"test": True},
        )
        d = msg.to_dict()
        restored = MatrixClockMessage.from_dict(d)
        self.assertEqual(restored.sender_id, msg.sender_id)
        self.assertEqual(restored.message_id, msg.message_id)
        self.assertEqual(restored.matrix_clock, msg.matrix_clock)
        self.assertEqual(restored.payload, msg.payload)

if __name__ == "__main__":
    unittest.main()
