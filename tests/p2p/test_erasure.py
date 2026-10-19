import unittest
from gossipmesh.p2p.erasure import ErasureCoder
from gossipmesh.p2p.protocol import GossipProtocol


class TestErasureCoding(unittest.TestCase):
    def test_encoder_decoder_happy_path(self):
        coder = ErasureCoder(data_fragments=3, parity_fragments=2)
        message = b"Hello GossipMesh Partition Resiliency State Payload!"
        fragments = coder.encode(message)
        self.assertEqual(len(fragments), 5)

        # Drop some fragments (simulate loss)
        available = [fragments[0], fragments[2], fragments[3]]
        decoded = coder.decode(available, len(message))
        self.assertEqual(decoded, message)

    def test_protocol_fragment_propagation(self):
        proto = GossipProtocol(node_id="node-1", data_fragments=2, parity_fragments=1)
        payload = b"Distributed state synchronization packet"
        packets = proto.prepare_payload(payload)
        self.assertEqual(len(packets), 3)

        receiver = GossipProtocol(node_id="node-2", data_fragments=2, parity_fragments=1)
        # Send subset of fragments
        res1 = receiver.receive_fragment(
            packets[0]["packet_id"], packets[0]["frag_index"], packets[0]["data"], packets[0]["original_size"]
        )
        self.assertEqual(res1, b"")
        res2 = receiver.receive_fragment(
            packets[1]["packet_id"], packets[1]["frag_index"], packets[1]["data"], packets[1]["original_size"]
        )
        self.assertEqual(res2, payload)

    def test_insufficient_fragments(self):
        coder = ErasureCoder(data_fragments=2, parity_fragments=1)
        fragments = coder.encode(b"test data")
        with self.assertRaises(ValueError):
            coder.decode([fragments[0]], len(b"test data"))


if __name__ == "__main__":
    unittest.main()
