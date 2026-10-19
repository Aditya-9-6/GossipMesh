import unittest
import threading
from gossipmesh.p2p.routing import ConcurrentSkipListRoutingTable


class TestConcurrentSkipListRoutingTable(unittest.TestCase):
    def test_insert_and_search(self):
        table = ConcurrentSkipListRoutingTable(capacity=10)
        table.insert("peer_a", 10.5, 2.1)
        table.insert("peer_b", 5.0, 1.2)

        res_a = table.search("peer_a")
        self.assertIsNotNone(res_a)
        self.assertEqual(res_a, (10.5, 2.1))

        res_b = table.search("peer_b")
        self.assertIsNotNone(res_b)
        self.assertEqual(res_b, (5.0, 1.2))

        self.assertIsNone(table.search("nonexistent"))

    def test_update_existing(self):
        table = ConcurrentSkipListRoutingTable()
        table.insert("peer_a", 10.0, 5.0)
        table.insert("peer_a", 2.0, 1.0)
        self.assertEqual(table.search("peer_a"), (2.0, 1.0))
        self.assertEqual(table.size, 1)

    def test_capacity_bound(self):
        table = ConcurrentSkipListRoutingTable(capacity=3)
        table.insert("peer_1", 1.0, 1.0)
        table.insert("peer_2", 2.0, 1.0)
        table.insert("peer_3", 3.0, 1.0)
        table.insert("peer_4", 0.5, 1.0)
        self.assertEqual(table.size, 3)
        self.assertIsNone(table.search("peer_3"))

    def test_delete(self):
        table = ConcurrentSkipListRoutingTable()
        table.insert("peer_a", 1.0, 1.0)
        self.assertTrue(table.delete("peer_a"))
        self.assertIsNone(table.search("peer_a"))
        self.assertFalse(table.delete("peer_a"))

    def test_concurrent_access(self):
        table = ConcurrentSkipListRoutingTable(capacity=100)

        def worker(start, end):
            for i in range(start, end):
                table.insert(f"peer_{i}", float(i), float(i))
                table.search(f"peer_{i}")

        threads = [threading.Thread(target=worker, args=(i * 20, (i + 1) * 20)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertLessEqual(table.size, 100)


if __name__ == "__main__":
    unittest.main()
