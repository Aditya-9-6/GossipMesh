import asyncio
import pytest
from pathlib import Path
from gossipmesh.storage.journal import JournalLog, JournalCorruptionError


@pytest.mark.asyncio
async def test_journal_basic_append_and_replay(tmp_path: Path):
    journal_path = tmp_path / "gossip.journal"
    journal = JournalLog(journal_path)

    seq1 = await journal.append_async({"node_id": "node-1", "state": "joining"})
    seq2 = await journal.append_async({"node_id": "node-2", "state": "active"})

    assert seq1 == 1
    assert seq2 == 2

    records = journal.replay()
    assert len(records) == 2
    assert records[0] == (1, {"node_id": "node-1", "state": "joining"})
    assert records[1] == (2, {"node_id": "node-2", "state": "active"})
    journal.close()


@pytest.mark.asyncio
async def test_journal_restart_recovery(tmp_path: Path):
    journal_path = tmp_path / "gossip.journal"
    journal = JournalLog(journal_path)
    await journal.append_async({"event": "heartbeat", "clock": 10})
    journal.close()

    # Simulate restart by reopening the same journal file
    journal2 = JournalLog(journal_path)
    records = journal2.replay()
    assert len(records) == 1
    assert records[0][1]["event"] == "heartbeat"

    # Append next record, sequence should continue correctly
    seq = await journal2.append_async({"event": "heartbeat", "clock": 11})
    assert seq == 2
    journal2.close()


@pytest.mark.asyncio
async def test_journal_compaction(tmp_path: Path):
    journal_path = tmp_path / "gossip.journal"
    journal = JournalLog(journal_path)
    await journal.append_async({"v": 1})
    await journal.append_async({"v": 2})
    await journal.append_async({"v": 3})

    journal.compact({"v": 3, "compacted": True})

    records = journal.replay()
    assert len(records) == 1
    assert records[0][0] == 1
    assert records[0][1] == {"v": 3, "compacted": True}
    journal.close()


def test_journal_corruption_detection(tmp_path: Path):
    journal_path = tmp_path / "gossip.journal"
    journal = JournalLog(journal_path)
    journal.append({"test": "data"})
    journal.close()

    # Corrupt payload byte on disk
    with open(journal_path, "r+b") as f:
        f.seek(-5, 2)
        f.write(b"\xFF\xFF\xFF\xFF\xFF")

    with pytest.raises(JournalCorruptionError):
        JournalLog(journal_path)
