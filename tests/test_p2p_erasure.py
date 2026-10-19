import unittest
import asyncio
from gossipmesh.p2p.erasure import ErasureCoder, BlockPool
from gossipmesh.p2p.transport import GossipTransport


class TestErasureCoder(unittest.TestCase):
    def setUp(self):
        self.coder = ErasureCoder(k=4, m=2, block_size=64)

    def test_block_pool(self):
        pool = BlockPool(block_size=32, max_pool_size=5)
        buf = pool.acquire()
        self.assertEqual(len(buf), 32)
        pool.release(buf)
        buf2 = pool.acquire()
        self.assertEqual(len(buf2), 32)

    def test_encode_decode_perfect(self):
        payload = b"Hello GossipMesh Erasure-Coded Decentralized Mesh Network!" * 2
        fragments = self.coder.encode(payload)
        self.assertEqual(len(fragments), 6)  # k=4 + m=2

        # Decode using exact k fragments
        reconstructed = self.coder.decode(fragments[:4], original_size=len(payload))
        self.assertEqual(reconstructed, payload)

    def test_encode_decode_with_loss(self):
        payload = b"Resilient multi-path agent swarm broadcasting state updates." * 3
        fragments = self.coder.encode(payload)

        # Drop 2 fragments (e.g. simulate packet loss on disjoint paths)
        surviving_fragments = [fragments[0], fragments[2], fragments[3], fragments[5]]
        self.assertEqual(len(surviving_fragments), 4)

        reconstructed = self.coder.decode(surviving_fragments, original_size=len(payload))
        self.assertEqual(reconstructed, payload)

    def test_insufficient_fragments(self):
        payload = b"Test insufficient fragments exception."
        fragments = self.coder.encode(payload)

        # Provide only 3 fragments when k=4 is required
        insufficient = fragments[:3]
        with self.assertRaises(ValueError):
            self.coder.decode(insufficient)


class TestGossipTransportErasure(unittest.TestCase):
    def test_transport_erasure_integration(self):
        async def run():
            transport = GossipTransport(node_id="node-1", k=3, m=1)
            received_messages = []

            transport.register_handler("swarm", lambda p: received_messages.append(p))

            payload = {"task": "refactor_module", "priority": 1}
            success = await transport.send_payload("node-2", payload, use_erasure=True)
            self.assertTrue(success)
            metrics = await transport.get_telemetry_metrics()
            self.assertGreater(metrics["bytes_sent"], 0)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
