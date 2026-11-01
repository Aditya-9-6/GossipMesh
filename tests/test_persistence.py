"""
Unit tests for the memory-mapped journaling ledger module.
"""

import os
import tempfile
import threading
import pytest

from gossipmesh.persistence import JournalingLedger


def test_ledger_append_and_recover():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_gossip.journal")

        with JournalingLedger(path) as ledger:
            p1 = b"node_state_alpha_1"
            p2 = b"node_state_beta_2"
            p3 = b"node_state_gamma_3"

            ledger.append(p1)
            ledger.append(p2)
            ledger.append(p3)

        # Re-open and verify recovery
        with JournalingLedger(path) as ledger:
            recovered = ledger.recover()
            assert recovered == [b"node_state_alpha_1", b"node_state_beta_2", b"node_state_gamma_3"]


def test_ledger_corruption_truncation():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "corrupt_gossip.journal")

        ledger = JournalingLedger(path)
        ledger.append(b"valid_frame_1")
        ledger.append(b"valid_frame_2")
        ledger.close()

        # Corrupt the file after valid frames
        with open(path, "r+b") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.write(b"CORRUPTED_GARBAGE_DATA_1234567890")

        # Re-open ledger; should recover only valid frames up to corruption
        with JournalingLedger(path) as ledger:
            recovered = ledger.recover()
            assert recovered == [b"valid_frame_1", b"valid_frame_2"]


def test_concurrent_ledger_appends():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "concurrent_gossip.journal")
        ledger = JournalingLedger(path, initial_size=1024 * 1024)

        num_threads = 10
        iterations_per_thread = 50

        def worker(thread_idx: int):
            for i in range(iterations_per_thread):
                payload = f"thread-{thread_idx}-msg-{i}".encode()
                ledger.append(payload)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        recovered = ledger.recover()
        ledger.close()

        assert len(recovered) == num_threads * iterations_per_thread
