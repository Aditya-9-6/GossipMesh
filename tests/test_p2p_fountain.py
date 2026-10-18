import unittest
from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder

class TestP2PFountain(unittest.TestCase):
    def test_encoder_decoder_roundtrip(self):
        payload = b"Hello, GossipMesh Asynchronous Fountain-Code Mesh Network!"
        chunk_size = 16
        encoder = FountainEncoder(payload, chunk_size=chunk_size, field_size=257)
        self.assertGreater(encoder.k, 0)

        decoder = FountainDecoder(k=encoder.k, chunk_size=chunk_size, field_size=257)

        # Feed more packets than k to ensure robust recovery under lossy conditions
        packets_fed = 0
        for _ in range(encoder.k + 5):
            coeffs, coded_chunk = encoder.generate_packet()
            if decoder.add_packet(coeffs, coded_chunk):
                packets_fed += 1
            if decoder.is_complete():
                break

        self.assertTrue(decoder.is_complete())
        recovered = decoder.decode()
        self.assertTrue(recovered.startswith(payload[:20]))

    def test_invalid_packet_handling(self):
        encoder = FountainEncoder(b"test payload", chunk_size=8, field_size=257)
        decoder = FountainDecoder(k=encoder.k, chunk_size=8, field_size=257)

        res = decoder.add_packet([1, 2], b"short")
        self.assertFalse(res)
        self.assertFalse(decoder.is_complete())
        self.assertIsNone(decoder.decode())

if __name__ == '__main__':
    unittest.main()
