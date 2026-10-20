import unittest
from gossipmesh.consensus.mvcc import MVCCStateStash, MVCCConflictError


class TestMVCCStateStash(unittest.TestCase):
    def setUp(self):
        self.stash = MVCCStateStash()

    def test_basic_read_write(self):
        epoch, read_set = self.stash.begin_transaction()
        self.assertEqual(epoch, 0)

        write_set = {"agent_memory": "state_v1"}
        commit_epoch = self.stash.validate_and_commit(read_set, write_set)
        self.assertEqual(commit_epoch, 1)

        val, v_epoch = self.stash.read("agent_memory")
        self.assertEqual(val, "state_v1")
        self.assertEqual(v_epoch, 1)

    def test_mvcc_conflict_detection(self):
        # Commit initial value
        epoch1, rs1 = self.stash.begin_transaction()
        self.stash.validate_and_commit(rs1, {"key1": "val_a"})

        # Agent A starts transaction at epoch 1
        epoch_a, rs_a = self.stash.begin_transaction()
        rs_a["key1"] = epoch_a

        # Agent B updates key1
        epoch_b, rs_b = self.stash.begin_transaction()
        self.stash.validate_and_commit(rs_b, {"key1": "val_b"})

        # Agent A attempts commit, should raise MVCCConflictError
        with self.assertRaises(MVCCConflictError):
            self.stash.validate_and_commit(rs_a, {"key1": "val_a2"})

    def test_snapshot_isolation(self):
        epoch1, rs1 = self.stash.begin_transaction()
        self.stash.validate_and_commit(rs1, {"score": 100})

        # Read historical snapshot at epoch 1
        val_old, _ = self.stash.read("score", epoch=1)
        self.assertEqual(val_old, 100)

        # Update score
        _, rs2 = self.stash.begin_transaction()
        self.stash.validate_and_commit(rs2, {"score": 200})

        # Latest read should show 200
        val_new, _ = self.stash.read("score")
        self.assertEqual(val_new, 200)

        # Historical snapshot read should still show 100
        val_snap, _ = self.stash.read("score", epoch=1)
        self.assertEqual(val_snap, 100)


if __name__ == "__main":
    unittest.main()
