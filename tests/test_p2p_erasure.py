import unittest
from gossipmesh.p2p.erasure import ErasureCoder

class TestErasureCoder(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        coder = ErasureCoder(k=4, m=2)
        payload = b"Hello GossipMesh P2P Erasure Coding Protocol!"
        
        shards = coder.encode(payload)
        self.assertEqual(len(shards), 6)
        
        # Simulate packet loss: drop 2 shards (e.g. drop one data, one parity)
        available_shards = [shards[0], shards[1], shards[2], shards[4]]
        
        decoded = coder.decode(available_shards, original_length=len(payload))
        self.assertEqual(decoded, payload)

    def test_insufficient_shards_raises_error(self):
        coder = ErasureCoder(k=4, m=2)
        payload = b"Testing failure condition for insufficient shards."
        shards = coder.encode(payload)
        
        # Only provide 3 shards when k=4 is required
        sparse_shards = shards[:3]
        with self.assertRaises(ValueError):
            coder.decode(sparse_shards, original_length=len(payload))

    def test_empty_payload(self):
        coder = ErasureCoder(k=2, m=1)
        shards = coder.encode(b"")
        self.assertEqual(len(shards), 3)
        decoded = coder.decode(shards[:2], original_length=0)
        self.assertEqual(decoded, b"")

if __name__ == "__main__":
    unittest.main()
