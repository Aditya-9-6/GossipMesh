import unittest
from gossipmesh.core.merkle import MerkleDAG

class TestMerkleDAG(unittest.TestCase):
    def test_empty_dag(self):
        dag = MerkleDAG()
        self.assertIsNone(dag.root_hash)
        self.assertEqual(dag.get_divergent_keys(None), [])

    def test_single_element_dag(self):
        dag = MerkleDAG({"agent_1": "state_a"})
        self.assertIsNotNone(dag.root_hash)
        dag2 = MerkleDAG({"agent_1": "state_a"})
        self.assertEqual(dag.root_hash, dag2.root_hash)
        self.assertEqual(dag.get_divergent_keys(dag2.root_hash), [])

    def test_divergence_detection(self):
        dag1 = MerkleDAG({"a": "1", "b": "2"})
        dag2 = MerkleDAG({"a": "1", "b": "3"})
        self.assertNotEqual(dag1.root_hash, dag2.root_hash)
        divergent = dag1.reconcile(dag2.root_hash, dag2._data)
        self.assertIn("b", divergent)

    def test_proof_generation(self):
        dag = MerkleDAG({"agent_a": "v1", "agent_b": "v2", "agent_c": "v3"})
        proof = dag.generate_proof("agent_b")
        self.assertIsInstance(proof, list)

    def test_symmetric_reconciliation(self):
        dag1 = MerkleDAG({"k1": "v1", "k2": "v2"})
        dag2 = MerkleDAG({"k1": "v1", "k3": "v3"})
        diff = dag1.reconcile(dag2.root_hash, dag2._data)
        self.assertEqual(set(diff), {"k2", "k3"})

if __name__ == "__main__":
    unittest.main()
