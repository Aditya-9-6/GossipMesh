from gossipmesh.p2p.routing import ConcurrentSkipListRoutingTable

for i in range(100):
    table = ConcurrentSkipListRoutingTable(capacity=3)
    table.insert("peer_1", 1.0, 1.0)
    table.insert("peer_2", 2.0, 1.0)
    table.insert("peer_3", 3.0, 1.0)
    table.insert("peer_4", 0.5, 1.0)

    if table.search("peer_3") is not None:
        print(f"Failed at iteration {i}: peer_3 is still in the table!")
        break
