with open("gossipmesh/p2p/routing.py", "r") as f:
    data = f.read()

# _evict_worst in ConcurrentSkipListRoutingTable is broken.
# It sets worst_score = float("-inf") and then if nxt.score > worst_score it updates worst_node.
# This means it evicts the node with the highest score! (which is peer_3 = 3.0)
# But wait! If worst_node = peer_3, why is peer_3 still in the table?
# Because the delete logic inside _evict_worst only checks up to self.level.
# If worst_node has level > self.level, it might not be fully removed.
# Actually, the update array is built by searching for worst_node.
# Let's fix the logic in _evict_worst to properly use delete(worst_node.key)
data = data.replace(
    """    def _evict_worst(self) -> None:
        curr = self.head
        worst_node = None
        worst_score = float("-inf")
        while curr.forward[0]:
            nxt = curr.forward[0]
            if nxt.score > worst_score:
                worst_score = nxt.score
                worst_node = nxt
            curr = nxt

        if not worst_node:
            return

        update = [None] * self.max_level
        curr = self.head
        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] and curr.forward[i] != worst_node:
                curr = curr.forward[i]
            update[i] = curr

        for i in range(len(worst_node.forward)):
            if i < len(update) and update[i] and update[i].forward[i] == worst_node:
                update[i].forward[i] = worst_node.forward[i]

        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self.size -= 1""",
    """    def _evict_worst(self) -> None:
        curr = self.head
        worst_node = None
        worst_score = float("-inf")
        while curr.forward[0]:
            nxt = curr.forward[0]
            if nxt.score > worst_score:
                worst_score = nxt.score
                worst_node = nxt
            curr = nxt

        if not worst_node:
            return

        # It's safer to just delete using the existing robust delete logic,
        # but since we are already inside a lock, we must not call self.delete
        # (which also acquires the lock) to avoid deadlock.
        # However, the class uses threading.Lock(), not RLock, so calling delete() would deadlock.
        # We will duplicate the logic of delete() here.
        key = worst_node.key
        update = [None] * self.max_level
        curr = self.head
        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] and curr.forward[i].key < key:
                curr = curr.forward[i]
            update[i] = curr

        curr = curr.forward[0]
        if not curr or curr.key != key:
            return

        for i in range(self.level):
            if update[i].forward[i] != curr:
                break
            update[i].forward[i] = curr.forward[i]

        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self.size -= 1""",
)

with open("gossipmesh/p2p/routing.py", "w") as f:
    f.write(data)
