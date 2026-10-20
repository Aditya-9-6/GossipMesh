import unittest
from typing import Any, Dict, List, Optional, Tuple, Set, Union, Callable
from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder

class TestP2PFountainCodes(unittest.TestCase):
    def test_fountain_encode_decode_happy_path(self):
        payload = b"Hello GossipMesh Fountain Codes! High throughput resilient transmission."
        encoder = FountainEncoder(payload, symbol_size=16)
        decoder = FountainDecoder(symbol_size=16)
        
        stream = encoder.generate_stream(encoder.total_symbols + 5)
        decoded = None
        for sym in stream:
            symbol_id, total, checksum, chunk = sym
            complete = decoder.add_symbol(symbol_id, total, checksum, chunk)
            if complete:
                decoded = decoder.decode()
                break
                
        self.assertIsNotNone(decoded)
        self.assertTrue(decoded.startswith(b"Hello GossipMesh"))

    def test_fountain_lossy_channel(self):
        payload = b"Resilient P2P messaging over high loss mesh links via fountain symbols."
        encoder = FountainEncoder(payload, symbol_size=20)
        decoder = FountainDecoder(symbol_size=20)
        
        stream = encoder.generate_stream(encoder.total_symbols * 2)
        # Simulate high loss by dropping every second packet
        lossy_stream = [sym for i, sym in enumerate(stream) if i % 2 == 0]
        
        decoded = None
        for sym in lossy_stream:
            symbol_id, total, checksum, chunk = sym
            if decoder.add_symbol(symbol_id, total, checksum, chunk):
                decoded = decoder.decode()
                break
                
        self.assertIsNotNone(decoded)

    def test_decoder_incomplete(self):
        payload = b"Short test payload"
        encoder = FountainEncoder(payload, symbol_size=8)
        decoder = FountainDecoder(symbol_size=8)
        
        sym = encoder.get_symbol(0)
        decoder.add_symbol(*sym)
        self.assertFalse(decoder.is_complete())
        self.assertIsNone(decoder.decode())

if __name__ == '__main__':
    unittest.main()
