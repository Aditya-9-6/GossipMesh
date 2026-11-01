"""
Comprehensive Unit Tests for Erasure-Coded Fountain Fragments and P2P Transport.
"""

import unittest
from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder, FountainFragmentConfig, FountainFragment
from gossipmesh.p2p.transport import P2PTransport


class TestP2PFountain(unittest.TestCase):
    def test_fragment_serialization_roundtrip(self):
        frag = FountainFragment(
            session_id="test-sess-1",
            symbol_id=42,
            degree=3,
            indices=[0, 2, 5],
            payload=b"\x01\x02\x03\x04",
            total_chunks=10,
        )
        raw = frag.serialize()
        restored = FountainFragment.deserialize(raw)
        self.assertEqual(frag.session_id, restored.session_id)
        self.assertEqual(frag.symbol_id, restored.symbol_id)
        self.assertEqual(frag.degree, restored.degree)
        self.assertEqual(frag.indices, restored.indices)
        self.assertEqual(frag.payload, restored.payload)
        self.assertEqual(frag.total_chunks, restored.total_chunks)

    def test_fountain_encode_decode_resilience(self):
        original_data = b"Hello GossipMesh! Resilient distributed AI agent mesh payload broadcast test."
        config = FountainFragmentConfig(chunk_size=16)
        encoder = FountainEncoder(original_data, config)

        decoder = FountainDecoder(encoder.total_chunks, config.chunk_size)

        # Generate more symbols than total chunks to simulate high loss resilience
        symbols_needed = int(encoder.total_chunks * 1.5) + 2
        success = False
        for i in range(symbols_needed):
            sym = encoder.generate_symbol(i, "sess-abc")
            if decoder.add_fragment(sym):
                success = True
                break

        self.assertTrue(success)
        reassembled = decoder.get_reassembled_data(len(original_data))
        self.assertEqual(reassembled, original_data)

    def test_transport_broadcast_and_receipt(self):
        transport = P2PTransport("node-alpha")
        payload = b"Critical enterprise AI task deployment payload synchronization."
        fragments = transport.prepare_broadcast(payload, "session-xyz", 20)

        self.assertGreater(len(fragments), 0)

        completed = False
        result_data = None
        for raw_frag in fragments:
            done, data = transport.receive_fragment(raw_frag, len(payload))
            if done:
                completed = True
                result_data = data
                break

        self.assertTrue(completed)
        self.assertEqual(result_data, payload)


if __name__ == "__mainដែលមាន__":
    unittest.main()
