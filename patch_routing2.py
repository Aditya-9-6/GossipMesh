with open("gossipmesh/p2p/routing.py", "r") as f:
    data = f.read()

# the problem with _evict_worst is:
# it only finds the worst_node but since there are multiple levels, its forward pointers might not be updated correctly if len(worst_node.forward) > len(update). But wait!
