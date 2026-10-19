import unittest
from gossipmesh.core.merkle import MerkleDAG, hash_leaf, hash_nodes, compute_hash


class TestMerkleDAG(unittest.TestCase):
    def test_hash_primitives(self):
        h1 = compute_hash(b"test")
        self.assertEqual(len(h1), 64)

        leaf_h = hash_leaf("agent_1", "active")
        self.assertEqual(len(leaf_h), 64)

        parent_h = hash_nodes(leaf_h, leaf_h)
        self.assertEqual(len(parent_h), 64)

    def test_merkle_dag_empty(self):
        dag = MerkleDAG()
        self.assertEqual(dag.get_root_hash(), compute_hash(b""))
        self.assertEqual(dag.get_leaf_hashes(), {})

    def test_merkle_dag_single_node(self):
        dag = MerkleDAG({"agent_a": "status_ok"})
        root_hash = dag.get_root_hash()
        self.assertEqual(root_hash, hash_leaf("agent_a", "status_ok"))

    def test_merkle_dag_multiple_nodes(self):
        state1 = {"b": 2, "a": 1, "c": 3}
        dag1 = MerkleDAG(state1)

        state2 = {"a": 1, "b": 2, "c": 3}
        dag2 = MerkleDAG(state2)

        # Order of dict keys shouldn't matter since state is sorted
        self.assertEqual(dag1.get_root_hash(), dag2.get_root_hash())

    def test_state_reconciliation_divergence(self):
        dag_local = MerkleDAG({"agent_1": "v1", "agent_2": "v2"})
        dag_remote = MerkleDAG({"agent_1": "v1_modified", "agent_3": "v3"})

        remote_leaves = dag_remote.get_leaf_hashes()
        divergent = dag_local.get_divergent_keys(dag_remote.get_root_hash(), remote_leaves)

        # agent_1 has different values, agent_2 is only local, agent_3 is only remote
        self.assertIn("agent_1", divergent)
        self.assertIn("agent_2", divergent)
        self.assertIn("agent_3", divergent)

    def test_update_state(self):
        dag = MerkleDAG({"agent_1": "v1"})
        h_initial = dag.get_root_hash()

        dag.update_state("agent_1", "v2")
        h_updated = dag.get_root_hash()

        self.assertNotEqual(h_initial, h_updated)


if __name__ == "__main__":
    unittest.main()
