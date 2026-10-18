import unittest
from gossipmesh.consensus.state_machine import StateMachine
from gossipmesh.consensus.raft import RaftNode, RaftState, LogEntry


class TestStateMachine(unittest.TestCase):
    def test_apply_and_hashing(self):
        sm = StateMachine()
        res1 = sm.apply({"action": "SET", "key": "alpha", "value": 100})
        self.assertEqual(res1, 100)
        self.assertEqual(sm.applied_index, 1)

        res2 = sm.apply({"action": "SET", "key": "beta", "value": 200})
        self.assertEqual(res2, 200)

        hash1 = sm.get_state_hash()
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)

        # Test deletion
        del_res = sm.apply({"action": "DELETE", "key": "alpha"})
        self.assertEqual(del_res, 100)
        hash2 = sm.get_state_hash()
        self.assertNotEqual(hash1, hash2)


class TestRaftNode(unittest.TestCase):
    def setUp(self):
        self.node = RaftNode("node-1", ["node-2", "node-3"])

    def test_initial_state(self):
        self.assertEqual(self.node.state, RaftState.FOLLOWER)
        self.assertEqual(self.node.current_term, 0)
        self.assertIsNone(self.node.voted_for)

    def test_start_election(self):
        term, node_id, last_term, last_index = self.node.start_election()
        self.assertEqual(self.node.state, RaftState.CANDIDATE)
        self.assertEqual(term, 1)
        self.assertEqual(node_id, "node-1")
        self.assertEqual(self.node.voted_for, "node-1")

    def test_request_vote_handling(self):
        # Higher term updates follower term and grants vote
        resp = self.node.request_vote(term=1, candidate_id="node-2", last_log_term=0, last_log_index=0)
        self.assertTrue(resp["vote_granted"])
        self.assertEqual(self.node.current_term, 1)
        self.assertEqual(self.node.voted_for, "node-2")

        # Second vote request in same term from different candidate denied
        resp2 = self.node.request_vote(term=1, candidate_id="node-3", last_log_term=0, last_log_index=0)
        self.assertFalse(resp2["vote_granted"])

    def test_append_entries_and_commit(self):
        entry = LogEntry(term=1, index=1, command={"action": "SET", "key": "x", "value": 42})
        resp = self.node.append_entries(
            term=1,
            leader_id="node-2",
            prev_log_index=0,
            prev_log_term=0,
            entries=[entry.to_dict()],
            leader_commit=1
        )
        self.assertTrue(resp["success"])
        self.assertEqual(len(self.node.log), 1)
        self.assertEqual(self.node.commit_index, 1)
        self.assertEqual(self.node.last_applied, 1)
        self.assertEqual(self.node.state_machine._store["x"], 42)

    def test_client_write_leader_only(self):
        # Follower write should fail
        success = self.node.client_write({"action": "SET", "key": "y", "value": 10})
        self.assertFalse(success)

        # Force leader state
        self.node.state = RaftState.LEADER
        success_leader = self.node.client_write({"action": "SET", "key": "y", "value": 10})
        self.assertTrue(success_leader)
        self.assertEqual(len(self.node.log), 1)

    def test_log_compaction(self):
        self.node.log.append(LogEntry(term=1, index=1, command={"action": "SET", "key": "a", "value": 1}))
        self.node.log.append(LogEntry(term=1, index=2, command={"action": "SET", "key": "b", "value": 2}))
        self.assertEqual(len(self.node.log), 2)
        self.node.compact_log(1)
        self.assertEqual(len(self.node.log), 1)
        self.assertEqual(self.node.log[0].index, 2)


if __name__ == "__main__":
    unittest.main()
