import unittest
import time
from gossipmesh.p2p.fragmentation import MessageFragmenter, MessageReassembler, PacketFragment
from gossipmesh.p2p.transport import P2PTransport


class TestFragmentationAndReassembly(unittest.TestCase):
    def test_happy_path_fragmentation_reassembly(self):
        original_data = b"Hello GossipMesh! " * 500  # ~9KB payload
        chunk_size = 1024
        
        fragments = MessageFragmenter.fragment(original_data, chunk_size=chunk_size)
        self.assertTrue(len(fragments) > 1)
        
        reassembler = MessageReassembler()
        result = None
        for f in fragments:
            res = reassembler.add_fragment(f)
            if res is not None:
                result = res
                
        self.assertEqual(result, original_data)

    def test_empty_payload(self):
        original_data = b""
        fragments = MessageFragmenter.fragment(original_data, chunk_size=1024)
        self.assertEqual(len(fragments), 1)
        
        reassembler = MessageReassembler()
        result = reassembler.add_fragment(fragments[0])
        self.assertEqual(result, original_data)

    def test_crc_mismatch_raises_error(self):
        original_data = b"Sensitive payload data"
        fragments = MessageFragmenter.fragment(original_data, chunk_size=10)
        
        # Corrupt the payload of the first fragment
        fragments[0].payload = b"corrupted!"
        
        reassembler = MessageReassembler()
        with self.assertRaises(ValueError):
            for f in fragments:
                reassembler.add_fragment(f)

    def test_reassembly_timeout_eviction(self):
        original_data = b"Incomplete transmission"
        fragments = MessageFragmenter.fragment(original_data, chunk_size=10)
        
        # Use a short timeout of 0.1 seconds
        reassembler = MessageReassembler(timeout_seconds=0.1)
        
        # Add only the first fragment
        res = reassembler.add_fragment(fragments[0])
        self.assertIsNone(res)
        self.assertEqual(len(reassembler.buffers), 1)
        
        # Wait for timeout to elapse
        time.sleep(0.2)
        
        # Add second fragment, which should trigger eviction of the stale buffer
        # and start a new buffer or ignore missing parts
        # Since the first expired, adding fragment[1] will treat it as a new msg_id's first fragment if we pass it, 
        # but here fragments[1] has the same message_id. _evict_expired checks last_update.
        # Let's test by sending a new fragment for expired message_id
        # Eviction clears expired msg_ids.
        reassembler._evict_expired(time.time())
        self.assertEqual(len(reassembler.buffers), 0)

    def test_transport_wrapper(self):
        transport = P2PTransport(mtu=50)
        data = b"Transport integration test payload for chunking and transport layer verification."
        
        dicts = transport.prepare_outgoing(data)
        self.assertTrue(len(dicts) > 1)
        
        reassembled = None
        for d in dicts[:-1]:
            res = transport.handle_incoming_fragment(d)
            self.assertIsNone(res)
            
        reassembled = transport.handle_incoming_fragment(dicts[-1])
        self.assertEqual(reassembled, data)


if __name__ == "__main__":
    unittest.main()
