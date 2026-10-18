import unittest
from gossipmesh.consensus.checkpoint import StateCheckpoint
from gossipmesh.consensus.validator import EpochCheckpointValidator

class TestCheckpointConsensus(unittest.TestCase):
    def test_checkpoint_hash_and_signature(self):
        cp = StateCheckpoint(epoch=1, node_id="node_a", state_root="root_abc")
        h = cp.compute_hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

        secret = "secret_key_123"
        sig = cp.sign(secret)
        self.assertIsNotNone(sig)
        self.assertTrue(cp.verify_signature(secret))
        self.assertFalse(cp.verify_signature("wrong_secret"))

    def test_validator_quorum_achievement(self):
        # 4 nodes -> 2/3 + 1 = 3 nodes required for quorum
        keys = {"n1": "k1", "n2": "k2", "n3": "k3", "n4": "k4"}
        validator = EpochCheckpointValidator(total_nodes=4, secret_keys=keys)

        cp1 = StateCheckpoint(epoch=10, node_id="n1", state_root="root_alpha")
        cp1.sign("k1")
        cp2 = StateCheckpoint(epoch=10, node_id="n2", state_root="root_alpha")
        cp2.sign("k2")
        cp3 = StateCheckpoint(epoch=10, node_id="n3", state_root="root_alpha")
        cp3.sign("k3")

        self.assertTrue(validator.submit_checkpoint(cp1))
        self.assertFalse(validator.check_quorum(10))

        self.assertTrue(validator.submit_checkpoint(cp2))
        self.assertFalse(validator.check_quorum(10))

        self.assertTrue(validator.submit_checkpoint(cp3))
        self.assertTrue(validator.check_quorum(10))
        self.assertTrue(validator.is_finalized(10))
        self.assertEqual(validator.get_finalized_state_root(10), "root_alpha")

    def test_byzantine_fault_isolation(self):
        keys = {"n1": "k1", "byzantine_node": "bad_key"}
        validator = EpochCheckpointValidator(total_nodes=2, secret_keys=keys)

        bad_cp = StateCheckpoint(epoch=5, node_id="byzantine_node", state_root="root_bad")
        # Sign with wrong secret
        bad_cp.sign("wrong_secret")

        self.assertFalse(validator.submit_checkpoint(bad_cp))
        self.assertFalse(validator.is_finalized(5))

if __name__ == "__main__":
    unittest.main()
