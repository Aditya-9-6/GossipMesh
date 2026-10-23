import unittest
from gossipmesh.p2p.routing import ConcurrentSkipListRoutingTable


class TestConcurrentSkipListRoutingTable(unittest.TestCase):
    def test_insert_and_search(self):
        table = ConcurrentSkipListRoutingTable(capacity=10)
        table.insert("peer_a", 10.5, 2.1)
        table.insert("peer_b", 5.0, 1.2)

        res_a = table.search("peer_a")
        self.assertIsNotNone(res_a)
        self.assertEqual(res_a, (10.5, 2.1))

    def test_capacity_bound(self):
        table = ConcurrentSkipListRoutingTable(capacity=3)
        table.insert("peer_1", 1.0, 1.0)
        table.insert("peer_2", 2.0, 1.0)
        table.insert("peer_3", 3.0, 1.0)
        table.insert("peer_4", 0.5, 1.0)
        self.assertEqual(table.size, 3)

    def test_delete(self):
        table = ConcurrentSkipListRoutingTable()
        table.insert("peer_a", 1.0, 1.0)
        self.assertTrue(table.delete("peer_a"))
        self.assertFalse(table.delete("non_existent"))
