with open("gossipmesh/p2p/node.py", "r") as f:
    data = f.read()

# Wait, tests/test_p2p_pow.py: test_gossip_node_with_pow and test_gossip_node_invalid_pow_nonce_raises
# It expects GossipNode to mine pow on init if nonce is None, and to raise ValueError if nonce is invalid.
# Let's add that to __init__ of GossipNode.

data = data.replace(
"""        self.public_key = public_key
        self.pow_difficulty = pow_difficulty
        self.pow_nonce = pow_nonce""",
"""        self.public_key = public_key
        self.pow_difficulty = pow_difficulty

        if self.pow_difficulty > 0 and self.public_key:
            from gossipmesh.p2p.pow import verify_pow, mine_pow
            if pow_nonce is not None:
                if not verify_pow(self.public_key, pow_nonce, self.pow_difficulty):
                    raise ValueError("Invalid PoW nonce for given difficulty")
                self.pow_nonce = pow_nonce
            else:
                self.pow_nonce, _ = mine_pow(self.public_key, self.pow_difficulty)
        else:
            self.pow_nonce = pow_nonce"""
)

with open("gossipmesh/p2p/node.py", "w") as f:
    f.write(data)
