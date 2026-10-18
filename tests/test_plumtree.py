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

    def test_message_handling_and_graft(self):
        self.mesh.add_lazy_peer(
            "peer-C"
        )
        is_dup = self.mesh.handle_message("msg-1", "payload", "peer-C")
        self.assertFalse(is_dup)
        # Receiving from lazy peer grafts back to eager
        self.assertIn("peer-C", self.mesh.get_eager_peers())
        self.assertNotIn("peer-C", self.mesh.get_lazy_peers())

        # Duplicate message handling
        is_dup_second = self.mesh.handle_message("msg-1", "payload", "peer-C")
        self.assertTrue(is_dup_second)

class TestP2PRouter(unittest.TestCase):
    def setUp(self):
        self.router = P2PRouter("router-node")

    def test_router_routing(self):
        self.router.register_peer("peer-1", eager=True)
        self.router.register_peer("peer-2", eager=False)
        result = self.router.route_message("m-100", "data", "peer-2")
        self.assertFalse(result["is_duplicate"])
        self.assertIn("peer-2", result["forward_eager"])
        self.assertIn("peer-1", result["forward_eager"])

if __name__ == "__main__":
    unittest.main()
