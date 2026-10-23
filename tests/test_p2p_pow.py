import unittest
import tempfile
import shutil
from pathlib import Path
from gossipmesh.p2p.pow import calculate_pow_hash, verify_pow, mine_pow
from gossipmesh.p2p.node import GossipNode, GossipTopic


class TestP2PPow(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pow_mining_and_verification(self):
        pubkey = "test_pubkey_12345"
        difficulty = 2
        nonce, h = mine_pow(pubkey, difficulty)
        self.assertTrue(h.startswith("00"))
        self.assertTrue(verify_pow(pubkey, nonce, difficulty))

    def test_pow_invalid_verification(self):
        pubkey = "test_pubkey_12345"
        difficulty = 2
        self.assertFalse(verify_pow(pubkey, 999999, difficulty))

    def test_gossip_node_with_pow(self):
        difficulty = 1
        node = GossipNode(
            node_id="node_alpha", mesh_dir=self.test_dir, public_key="pub_alpha_key", pow_difficulty=difficulty
        )
        self.assertEqual(node.pow_difficulty, difficulty)
        self.assertTrue(verify_pow(node.public_key, node.pow_nonce, difficulty))

    def test_gossip_node_invalid_pow_nonce_raises(self):
        with self.assertRaises(ValueError):
            GossipNode(
                node_id="node_beta",
                mesh_dir=self.test_dir,
                public_key="pub_beta_key",
                pow_difficulty=2,
                pow_nonce=12345,
            )
