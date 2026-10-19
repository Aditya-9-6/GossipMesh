import unittest
import time
from gossipmesh.p2p.checkpointer import StateCheckpointer


class TestStateCheckpointer(unittest.TestCase):
    def test_snapshot_creation_performance(self):
        checkpointer = StateCheckpointer()
        for i in range(1000):
            checkpointer.update_state(f"agent_{i}", {"id": i, "load": 0.5})

        root_hash, duration_ms = checkpointer.create_snapshot()
        self.assertIsNotNone(root_hash)
        self.assertLess(duration_ms, 50.0, "Snapshot generation exceeded 50ms threshold")

    def test_verify_and_restore(self):
        checkpointer = StateCheckpointer()
        checkpointer.update_state("agent_alpha", {"status": "ready"})
        root_hash, _ = checkpointer.create_snapshot()

        self.assertTrue(checkpointer.verify_snapshot(root_hash))

        checkpointer.update_state("agent_beta", {"status": "busy"})
        self.assertTrue(checkpointer.restore_snapshot(root_hash))
        self.assertEqual(checkpointer.trie.get_root_hash(), root_hash)

    def test_invalid_snapshot(self):
        checkpointer = StateCheckpointer()
        self.assertFalse(checkpointer.verify_snapshot("nonexistent_hash"))
        self.assertFalse(checkpointer.restore_snapshot("nonexistent_hash"))


if __name__ == "__main__":
    unittest.main()
