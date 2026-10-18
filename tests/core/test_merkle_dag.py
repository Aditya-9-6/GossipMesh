import unittest
from gossipmesh.core.vector_clock import VectorClock
from gossipmesh.core.merkle_dag import MerkleDAG, MerkleDAGNode

class TestVectorClockAndMerkleDAG(unittest.TestCase):

    def test_vector_clock_operations(self):
        vc1 = VectorClock({"nodeA": 1})
        vc2 = VectorClock({"nodeA": 2})
        
        self.assertEqual(vc1.compare(vc2), 'LESS_THAN')
        self.assertEqual(vc2.compare(vc1), 'GREATER_THAN')
        
        vc3 = VectorClock({"nodeB": 1})
        self.assertEqual(vc1.compare(vc3), 'CONCURRENT')
        
        merged = vc1.merge(vc3)
        self.assertEqual(merged.to_dict(), {"nodeA": 1, "nodeB": 1})

    def test_merkle_dag_reconciliation(self):
        dag = MerkleDAG()
        vc_init = VectorClock({"nodeA": 1})
        node1 = dag.add_mutation("nodeA", {"action": "init"}, vc_init, parents=[])
        
        self.assertIn(node1.hash, dag.heads)
        
        # Concurrent forks
        vc_fork1 = VectorClock({"nodeA": 2, "nodeB": 0})
        node_fork1 = dag.add_mutation("nodeB", {"action": "fork1"}, vc_fork1, parents=[node1.hash])
        
        vc_fork2 = VectorClock({"nodeA": 1, "nodeC": 1})
        node_fork2 = dag.add_mutation("nodeC", {"action": "fork2"}, vc_fork2, parents=[node1.hash])
        
        self.assertIn(node_fork1.hash, dag.heads)
        self.assertIn(node_fork2.hash, dag.heads)
        self.assertNotIn(node1.hash, dag.heads)

    def test_merkle_dag_gc(self):
        dag = MerkleDAG()
        vc = VectorClock({"nodeA": 1})
        node1 = dag.add_mutation(
            node_id="nodeA",
            payload={"val": 1},
            vector_clock=vc,
            parents=[]
        )
        
        dag.gc({node1.hash})
        self.assertNotIn(node1.hash, dag.nodes)

if __name__ == '__main__':
    unittest.main()
