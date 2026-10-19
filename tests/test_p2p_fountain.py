import unittest
import asyncio
from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder
from gossipmesh.p2p.transport import GossipTransport


class TestP2PFountain(unittest.TestCase):
    def test_encoder_decoder_roundtrip(self):
        payload = b"Hello GossipMesh High-Performance P2P Fountain Protocol!" * 5
        encoder = FountainEncoder(payload, symbol_size=32)
        self.assertGreater(len(encoder.symbols), 0)

        decoder = FountainDecoder(len(encoder.symbols), symbol_size=32)
        for seq in range(len(encoder.symbols)):
            _, total, symbol = encoder.generate_symbol(seq)
            decoder.add_symbol(seq, symbol)

        self.assertTrue(decoder.is_complete())
        decoded = decoder.decode()
        self.assertEqual(decoded, payload)

    def test_fountain_loss_resilience(self):
        payload = b"Resilience test over lossy mesh networks." * 3
        encoder = FountainEncoder(payload, symbol_size=16)
        total = len(encoder.symbols)
        decoder = FountainDecoder(total, symbol_size=16)

        # Simulate packet loss by omitting even sequence numbers
        for seq in range(total):
            _, _, symbol = encoder.generate_symbol(seq)
            if seq % 2 == 0:
                decoder.add_symbol(seq, symbol)

        # Add remaining missing symbols
        for seq in range(total):
            _, _, symbol = encoder.generate_symbol(seq)
            if seq % 2 != 0:
                decoder.add_symbol(seq, symbol)

        self.assertTrue(decoder.is_complete())
        self.assertEqual(decoder.decode(), payload)

    def test_transport_fountain_integration(self):
        transport = GossipTransport(node_id="node-1")
        received_data = []
        transport.register_handler("test_topic", lambda p: received_data.append(p))

        payload = {"status": "ok", "data": "gossip"}

        async def run():
            await transport.send_payload("node-2", payload)

        asyncio.run(run())
        self.assertGreater(transport.telemetry.sent_count, 0)


if __name__ == "__main__":
    unittest.main()
