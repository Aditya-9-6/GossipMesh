import unittest
from gossipmesh.core.merkle import MerkleDAG, MerkleNode


class TestMerkleDAG(unittest.TestCase):
    def test_empty_dag(self):
        dag = MerkleDAG()
        self.assertIsNone(dag.get_root_hash())
        self.assertEqual(dag.get_state(), {})

    def test_single_element_dag(self):
        dag = MerkleDAG({"agent_1": {"status": "idle"}})
        root_hash = dag.get_root_hash()
        self.assertIsNotNone(root_hash)
        self.assertEqual(len(root_hash), 64)

    def test_deterministic_hashing(self):
        state_a = {"b": 2, "a": 1}
        state_b = {"a": 1, "b": 2}
        dag_a = MerkleDAG(state_a)
        dag_b = MerkleDAG(state_b)
        self.assertEqual(dag_a.get_root_hash(), dag_b.get_root_hash())

    def test_state_updates(self):
        dag = MerkleDAG({"agent_1": "active"})
        hash_before = dag.get_root_hash()
        dag.update_state("agent_1", "busy")
        hash_after = dag.get_root_hash()
        self.assertNotEqual(hash_before, hash_after)

        dag.remove_state("agent_1")
        self.assertIsNone(dag.get_root_hash())

    def test_find_divergences_identical(self):
        state = {"k1": "v1", "k2": "v2"}
        dag1 = MerkleDAG(state)
        dag2 = MerkleDAG(state)
        divergences = dag1.find_divergences(dag2.get_root_hash(), dag2.root, dag1.root)
        self.assertEqual(divergences, [])

    def test_find_divergences_different(self):
        dag1 = MerkleDAG({"k1": "v1", "k2": "v2"})
        dag2 = MerkleDAG({"k1": "v1", "k2": "v2_modified"})
        divergences = dag1.find_divergences(dag2.get_root_hash(), dag2.root, dag1.root)
        self.assertIn("k2", divergences)


if __name__ == "__main പ്രധാന__":
    unittest.main()
