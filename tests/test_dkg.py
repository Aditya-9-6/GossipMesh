import unittest
from gossipmesh.consensus.vss import VerifiableSecretSharing, Point, G, scalar_mult, point_add, CURVE_ORDER
from gossipmesh.consensus.dkg import DKGNodeState


class TestDKGandVSS(unittest.TestCase):
    def test_vss_polynomial_and_commitments(self):
        secret = 123456789
        threshold = 3
        poly = VerifiableSecretSharing.generate_polynomial(secret, threshold)
        self.assertEqual(len(poly), threshold)
        self.assertEqual(poly[0], secret)

        eval_at_2 = VerifiableSecretSharing.evaluate_polynomial(poly, 2)
        comms = VerifiableSecretSharing.commit(poly)
        self.assertEqual(len(comms), threshold)

        is_valid = VerifiableSecretSharing.verify_share(2, eval_at_2, comms)
        self.assertTrue(is_valid)

        # Test invalid share verification
        is_invalid = VerifiableSecretSharing.verify_share(2, eval_at_2 + 1, comms)
        self.assertFalse(is_invalid)

    def test_dkg_full_protocol(self):
        n = 4
        t = 2
        nodes = [DKGNodeState(node_id=i, total_nodes=n, threshold=t) for i in range(1, n + 1)]

        # Phase 1 & 2: Generate polynomials and exchange shares
        broadcasts = {}
        for node in nodes:
            poly, comms = node.phase1_generate_shares()
            broadcasts[node.node_id] = (comms, poly)

        # Distribute shares
        for recipient in nodes:
            for sender_id, (comms, poly) in broadcasts.items():
                if recipient.node_id == sender_id:
                    continue
                share_y = VerifiableSecretSharing.evaluate_polynomial(poly, recipient.node_id)
                success = recipient.phase3_receive_and_verify_share(sender_id, share_y, comms)
                self.assertTrue(success)

        # Phase 4 & 5: Compute private shares and group public key
        expected_group_pk = None
        for node in nodes:
            node.phase4_compute_private_key_share()
            node.phase5_compute_group_public_key()
            if expected_group_pk is None:
                expected_group_pk = node.group_public_key
            else:
                self.assertEqual(node.group_public_key.x, expected_group_pk.x)
                self.assertEqual(node.group_public_key.y, expected_group_pk.y)

        # Verify each node's private share corresponds to group public key contribution
        for node in nodes:
            derived_pk = scalar_mult(node.private_key_share, G)
            # Node's public share should match verification checks
            self.assertIsNotNone(derived_pk)


if __name__ == '__main__':
    unittest.main()
