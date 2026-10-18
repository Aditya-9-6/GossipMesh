import unittest
from gossipmesh.p2p.reconciliation.iblt import InvertibleBloomLookupTable
from gossipmesh.p2p.reconciliation.protocol import IBLTReconciliationProtocol

class TestIBLTReconciliation(unittest.TestCase):
    def setUp(self):
        self.size = 60
        self.num_hashes = 3
        self.value_size = 16
        self.protocol = IBLTReconciliationProtocol(size=self.size, num_hashes=self.num_hashes, value_size=self.value_size)

    def test_iblt_basic_insertion_and_recovery(self):
        iblt = InvertibleBloomLookupTable(size=self.size, num_hashes=self.num_hashes, value_size=self.value_size)
        items = {
            101: b'payload_one',
            102: b'payload_two',
            103: b'payload_three'
        }
        for k, v in items.items():
            iblt.insert(k, v)

        added, removed, success = iblt.list_entries()
        self.assertTrue(success)
        self.assertEqual(len(added), 3)
        self.assertEqual(len(removed), 0)
        recovered_keys = {item[0] for item in added}
        self.assertEqual(recovered_keys, set(items.keys()))

    def test_iblt_reconciliation_protocol(self):
        node_a_inv = {
            1: b'alpha',
            2: b'beta',
            3: b'gamma'
        }
        node_b_inv = {
            2: b'beta',
            3: b'gamma',
            4: b'delta'
        }

        iblt_b = self.protocol.create_iblt(node_b_inv)
        added, removed, success = self.protocol.reconcile(node_a_inv, iblt_b.serialize())
        
        self.assertTrue(success)
        # Node A has key 1 (missing in B -> added relative to B), Node A lacks key 4 (removed relative to B)
        added_keys = {item[0] for item in added}
        removed_keys = {item[0] for item in removed}
        
        self.assertIn(1, added_keys)
        self.assertIn(4, removed_keys)

    def test_iblt_collision_fallback(self):
        # Force a collision by creating a very small IBLT with many conflicting elements
        iblt = InvertibleBloomLookupTable(size=2, num_hashes=4, value_size=8)
        for i in range(50):
            iblt.insert(i, b'data')
        
        _, _, success = iblt.list_entries()
        # With size=2 and 50 elements, decoding should fail and trigger fallback
        self.assertFalse(success)

    def test_fallback_sync(self):
        local_inv = {10: b'x', 20: b'y'}
        remote_keys = [20, 30]
        missing = self.protocol.fallback_full_sync(local_inv, remote_keys)
        self.assertEqual(missing, {10: b'x'})

if __name__ == '__main__':
    unittest.main()
