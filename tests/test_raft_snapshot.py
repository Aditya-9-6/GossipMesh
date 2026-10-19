import unittest
from gossipmesh.consensus.raft import RaftLogCompactionEngine
from gossipmesh.p2p.snapshot import SnapshotTransferProtocol

class TestRaftAndSnapshot(unittest.TestCase):
    def test_raft_compaction_and_snapshot(self):
        engine = RaftLogCompactionEngine(window_size=5)
        self.assertFalse(engine.should_compact(3))
        
        engine.apply_entry(1, 1, {"agent_1": "idle"})
        engine.apply_entry(2, 1, {"agent_2": "active"})
        self.assertTrue(engine.should_compact(6))
        
        snapshot = engine.create_snapshot()
        self.assertEqual(snapshot["last_included_index"], 2)
        self.assertIn("checksum", snapshot)
        
        new_engine = RaftLogCompactionEngine()
        new_engine.restore_snapshot(snapshot)
        self.assertEqual(new_engine.state_tree["agent_1"], "idle")
        self.assertEqual(new_engine.last_included_index, 2)

    def test_snapshot_transfer_protocol(self):
        protocol = SnapshotTransferProtocol(chunk_size=16)
        snapshot = {"last_included_index": 10, "state_tree": {"key": "value" * 5}}
        
        chunks = protocol.serialize_and_chunk(snapshot)
        self.assertGreater(len(chunks), 1)
        
        restored = protocol.reassemble_and_verify(chunks)
        self.assertEqual(restored["last_included_index"], 10)
        self.assertEqual(restored["state_tree"]["key"], "value" * 5)

    def test_corrupted_snapshot_transfer(self):
        protocol = SnapshotTransferProtocol(chunk_size=16)
        snapshot = {"data": "test"}
        chunks = protocol.serialize_and_chunk(snapshot)
        
        # Corrupt chunk data
        chunks[0]["data"] = "00" * len(chunks[0]["data"])
        
        with self.assertRaises(ValueError):
            protocol.reassemble_and_verify(chunks)

if __name__ == '__main__':
    unittest.main()
