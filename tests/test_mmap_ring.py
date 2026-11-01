import pytest
from gossipmesh.transport.mmap_ring import MMapCircularRingBuffer


def test_mmap_ring_basic_io():
    ring = MMapCircularRingBuffer(capacity_bytes=1024)
    try:
        msg1 = b"Hello GossipMesh Zero-Copy"
        msg2 = b"Second P2P Packet"

        assert ring.write(msg1) is True
        assert ring.write(msg2) is True

        assert ring.read() == msg1
        assert ring.read() == msg2
        assert ring.read() is None
    finally:
        ring.close()


def test_mmap_ring_capacity_limit():
    ring = MMapCircularRingBuffer(capacity_bytes=64)
    try:
        large_msg = b"A" * 50
        # 4 bytes length + 50 bytes data = 54 bytes total (fits in 64 bytes)
        assert ring.write(large_msg) is True

        # Next write should exceed capacity
        assert ring.write(b"B" * 20) is False

        assert ring.read() == large_msg
        assert ring.read() is None
    finally:
        ring.close()
