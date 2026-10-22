from gossipmesh.p2p.routing import ConcurrentSkipListRoutingTable
import random

random.seed(42)  # Make it deterministic if possible

table = ConcurrentSkipListRoutingTable(capacity=3)
table.insert("peer_1", 1.0, 1.0)
table.insert("peer_2", 2.0, 1.0)
table.insert("peer_3", 3.0, 1.0)
table.insert("peer_4", 0.5, 1.0)

print(table.search("peer_1"))
print(table.search("peer_2"))
print(table.search("peer_3"))
print(table.search("peer_4"))
