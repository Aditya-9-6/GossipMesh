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
        is_dup1 = self.mesh.handle_message("msg-1", {"data": 123}, "peer-A")
        self.assertFalse(is_dup1)
        
        # Duplicate message from same or other peer triggers transition/detection
        is_dup2 = self.mesh.handle_message("msg-1", {"data": 123}, "peer-A")
        self.assertTrue(is_dup2)

    def test_router_integration(self):
        router = P2PRouter("node-1")
        router.register_peer("peer-X", eager=True)
        router.register_peer("peer-Y", eager=False)

        res = router.route_message("msg-100", "hello", "peer-X")
        self.assertFalse(res["is_duplicate"])
        self.assertIn("peer-Y", res["forward_lazy"])

if __name__ == "__main__":
    unittest.main()
