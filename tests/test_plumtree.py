import unittest
from gossipmesh.p2p.plumtree import PlumTreeMesh
from gossipmesh.p2p.router import P2PRouter

class TestPlumTreeMesh(unittest.TestCase):
    def setUp(self):
        self.mesh = PlumTreeMesh("node-1")

    def test_peer_management(self):
        self.mesh.add_eager_peer("peer-A")
        self.assertIn("peer-A", self.mesh.get_eager_peers())
        self.mesh.add_lazy_peer("peer-B")
        self.assertIn("peer-B", self.mesh.get_lazy_peers())
        self.mesh.remove_peer("peer-A")
        self.assertNotIn("peer-A", self.mesh.get_eager_peers())

    def test_message_handling_and_duplicates(self):
        self.mesh.add_eager_peer("peer-A")
        self.mesh.add_lazy_peer(
            "peer-B"
        )
        
        # First time seeing message should return False (not duplicate)
        is_dup1 = self.mesh.handle_message("msg-1", "payload-data", "peer-A")
        self.assertFalse(is_dup1)
        
        # Second time from same or eager peer should detect duplicate
        is_dup2 = self.mesh.handle_message("msg-1", "payload-data", "peer-A")
        self.assertTrue(is_dup2)
        
        # Receiving from lazy peer should graft back to eager
        is_dup3 = self.mesh.handle_message("msg-2", "payload-data-2", "peer-B")
        self.assertFalse(is_dup3)
        self.assertIn("peer-B", self.mesh.get_eager_peers())

class TestP2PRouter(unittest.TestCase):
    def setUp(self):
        self.router = P2PRouter("node-1")

    def test_router_workflow(self):
        self.router.register_peer("peer-1", eager=True)
        self.router.register_peer("peer-2", eager=False)
        
        res = self.router.route_message("m1", "data", "peer-1")
        self.assertFalse(res["is_duplicate"])
        self.assertIn("peer-2", res["forward_lazy"])

if __name__ == "__main__":
    unittest.main()
