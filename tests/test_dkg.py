"""
Unit tests for Feldman's VSS and Threshold Signature DKG protocol.
"""

import unittest

from gossipmesh.consensus.vss import VSSScheme
from gossipmesh.consensus.dkg import DKGNode, DistributedKeyGenerationProtocol


class TestDKGAndVSS(unittest.TestCase):
    def test_vss_polynomial_and_verification(self):
        vss = VSSScheme()
        secret = 123456789
        threshold = 3
        
        poly = vss.generate_polynomial(secret, threshold)
        self.assertEqual(len(poly), threshold)
        self.assertEqual(poly[0], secret)
        
        commitments = vss.create_commitments(poly)
        self.assertEqual(len(commitments), threshold)
        
        # Evaluate share at x = 2
        share_x = 2
        share_y = vss.evaluate_polynomial(poly, share_x)
        
        # Verify share
        is_valid = vss.verify_share(share_x, share_y, commitments)
        self.assertTrue(is_valid)

        # Tamper with share
        is_valid_tampered = vss.verify_share(share_x, share_y + 1, commitments)
        self.assertFalse(is_valid_tampered)

    def test_lagrange_secret_reconstruction(self):
        vss = VSSScheme()
        secret = 987654321
        threshold = 3
        
        poly = vss.generate_polynomial(secret, threshold)
        shares = [(i, vss.evaluate_polynomial(poly, i)) for i in range(1, 5)]
        
        # Reconstruct using any subset of size >= threshold
        subset = shares[:threshold]
        reconstructed = vss.lagrange_interpolate(subset, evaluate_at=0)
        self.assertEqual(reconstructed, secret)

    def test_dkg_protocol_execution(self):
        total_nodes = 5
        threshold = 3
        
        nodes = [
            DKGNode(node_id=f"node-{i}", node_index=i, total_nodes=total_nodes, threshold=threshold)
            for i in range(1, total_nodes + 1)
        ]
        
        dkg_protocol = DistributedKeyGenerationProtocol(nodes, threshold)
        success = dkg_protocol.run_dkg_setup()
        
        self.assertTrue(success)
        
        # Verify all nodes have matching collective public keys and generated private shares
        first_pub_key = nodes[0].collective_public_key
        for node in nodes:
            self.assertIsNotNone(node.node_private_share)
            self.assertEqual(node.collective_public_key, first_pub_key)


if __name__ == "__main અમારા__":
    unittest.main()
