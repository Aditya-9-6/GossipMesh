import unittest
from gossipmesh.p2p.matrix_clock import MatrixClock


class TestMatrixClock(unittest.TestCase):
    def setUp(self):
        self.clock = MatrixClock(node_id="node-A", max_window=3)

    def test_initial_state(self):
        self.assertEqual(self.clock.get_clock(), {"node-A": 0})

    def test_increment(self):
        c = self.clock.increment()
        self.assertEqual(c["node-A"], 1)
        self.assertEqual(self.clock.get_clock(), {"node-A": 1})

    def test_update(self):
        self.clock.update({"node-B": 5, "node-C": 2})
        self.assertEqual(self.clock.get_clock(), {"node-A": 0, "node-B": 5, "node-C": 2})

    def test_satisfies_causality(self):
        # Local state: node-A: 0
        # Sender node-B should have remote[node-B] == 1 and others <= local
        self.assertTrue(self.clock.satisfies_causality("node-B", {"node-B": 1}))
        self.assertFalse(self.clock.satisfies_causality("node-B", {"node-B": 2}))
        self.assertFalse(self.clock.satisfies_causality("node-B", {"node-B": 1, "node-C": 1}))

    def test_buffer_and_poll_deliverable(self):
        # Node A at 0. Message from B with clock {"node-B": 1} is deliverable.
        # Message from C with clock {"node-C": 2} is out-of-order and buffered.
        self.clock.buffer_payload("node-C", {"node-C": 2}, "payload-C2")
        self.clock.buffer_payload(
            "node-B", {"node-B": 1, "node-C": 1}, "payload-B1"
        )  # depends on C:1 which isn't met yet

        delivered = self.clock.poll_deliverable()
        self.assertEqual(delivered, [])

        # Deliver first message for B directly satisfying causality
        self.clock.buffer_payload("node-B", {"node-B": 1}, "payload-B1")
        delivered = self.clock.poll_deliverable()
        self.assertEqual(delivered, ["payload-B1"])

    def test_max_window_bounds(self):
        # max_window is set to 3
        self.clock.buffer_payload("node-X", {"node-X": 10}, "stale-1")
        self.clock.buffer_payload("node-X", {"node-X": 11}, "stale-2")
        self.clock.buffer_payload("node-X", {"node-X": 12}, "msg-3")
        self.clock.buffer_payload("node-X", {"node-X": 13}, "msg-4")

        # stale-1 should have been dropped due to max_window limit
        self.assertEqual(len(self.clock._buffer), 3)
        self.assertEqual(self.clock._buffer[0][2], "stale-2")


if __name__ == "__main__":
    unittest.main()
