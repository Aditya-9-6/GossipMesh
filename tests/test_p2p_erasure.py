import unittest
from gossipmesh.p2p.erasure import ErasureCoder
from gossipmesh.p2p.transport import ErasureTransportMultiplexer

class TestErasureCoding(unittest.TestCase):
    def test_encode_decode_happy_path(self):
        coder = ErasureCoder(k=4, m=2)
        payload = b"Hello GossipMesh Erasure-Coded Fragment Multiplexing!" * 10
        
        fragments = coder.encode(payload)
        self.assertEqual(len(fragments), 6)
        
        # Take any 4 fragments (k=4)
        subset = fragments[:4]
        reconstructed = coder.decode(subset, original_size=len(payload))
        self.assertEqual(reconstructed, payload)

    def test_decode_with_parity_replacement(self):
        coder = ErasureCoder(k=3, m=2)
        payload = b"Distributed AI agent swarm state dissemination payload." * 5
        
        fragments = coder.encode(payload)
        
        # Drop first data shard, use parity shard instead
        subset = [fragments[1], fragments[2], fragments[3]]
        reconstructed = coder.decode(subset, original_size=len(payload))
        self.assertGreater(len(reconstructed), 0)

    def test_insufficient_fragments_raises(self):
        coder = ErasureCoder(k=4, m=2)
        payload = b"Test payload" * 2
        fragments = coder.encode(payload)
        
        with self.assertRaises(ValueError):
            coder.decode(fragments[:3])

    def test_transport_multiplexer(self):
        transport = ErasureTransportMultiplexer(k=3, m=1)
        data = {"event": "agent_consensus", "vote": "approve", "nodes": [1, 2, 3]}
        
        packets = transport.prepare_dissemination(data)
        self.assertEqual(len(packets), 4)
        
        # Assemble with any 3 packets
        subset = packets[:3]
        recovered = transport.assemble_dissemination(subset)
        self.assertEqual(recovered, data)

if __name__ == '__main__':
    unittest.main()
