import unittest
import zlib
from gossipmesh.p2p.fragmentation import PacketFragment, PacketFragmenter, PacketReassembler
from gossipmesh.p2p.transport import P2PTransport


class TestPacketFragmentation(unittest.TestCase):
    def test_fragmentation_and_reassembly_roundtrip(self):
        payload = b"A" * 5000
        message_id = "msg-test-123"
        fragmenter = PacketFragmenter(mtu=500)
        fragments = fragmenter.fragment(message_id, payload)

        self.assertGreater(len(fragments), 1)

        reassembler = PacketReassembler()
        reassembled = None

        # Feed fragments out of order to test sliding reassembly
        shuffled_frags = list(reversed(fragments))
        for i, frag in enumerate(shuffled_frags):
            serialized = frag.serialize()
            deserialized = PacketFragment.deserialize(serialized)
            res = reassembler.add_fragment(deserialized)
            if i < len(shuffled_frags) - 1:
                self.assertIsNone(res)
            else:
                reassembled = res

        self.assertEqual(reassembled, payload)

    def test_crc32_validation_failure(self):
        payload = b"Hello GossipMesh P2P!"
        message_id = "msg-bad-crc"
        fragmenter = PacketFragmenter(mtu=200)
        fragments = fragmenter.fragment(message_id, payload)

        # Corrupt crc32 or data
        fragments[0].crc32 = 0xDEADBEEF

        reassembler = PacketReassembler()
        with self.assertRaises(ValueError):
            for frag in fragments:
                reassembler.add_fragment(frag)

    def test_p2p_transport_fragmentation(self):
        transport = P2PTransport(mtu=300)
        payload = b"Distributed AI Agent Payload" * 10
        success = transport.send_gossip_sync("peer-1", payload)
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
