import pytest
from gossipmesh.p2p.shm_ringbuffer import SharedMemoryRingBuffer


def test_shm_ringbuffer_lifecycle():
    buffer_name = "test_gossipmesh_shm_lifecycle"
    # Ensure cleanup if previous test failed
    try:
        temp_buf = SharedMemoryRingBuffer(name=buffer_name, create=False)
        temp_buf.close()
        temp_buf.unlink()
    except Exception:
        pass

    ring = SharedMemoryRingBuffer(name=buffer_name, capacity=4, max_msg_size=64, create=True)
    try:
        assert ring.qsize() == 0
        
        # Push items
        assert ring.is_full() if hasattr(ring, 'is_full') else True  # sanity
        assert ring.push(b"agent-msg-1") is True
        assert ring.push(b"agent-msg-2") is True
        assert ring.qsize() == 2

        # Pop items
        assert ring.pop() == b"agent-msg-1"
        assert ring.qsize() == 1
        assert ring.pop() == b"agent-msg-2"
        assert ring.qsize() == 0
        assert ring.pop() is None
    finally:
        ring.close()
        ring.unlink()


def test_shm_ringbuffer_capacity_bounds():
    buffer_name = "test_gossipmesh_shm_bounds"
    try:
        temp_buf = SharedMemoryRingBuffer(name=buffer_name, create=False)
        temp_buf.close()
        temp_buf.unlink()
    except Exception:
        pass

    # Capacity is 3, but ring buffer usable slots = capacity - 1 due to circular buffer convention
    ring = SharedMemoryRingBuffer(name=buffer_name, capacity=3, max_msg_size=32, create=True)
    try:
        assert ring.push(b"m1") is True
        assert ring.push(b"m2") is True
        # 3rd push should fail because capacity is 3 (max 2 items stored to distinguish full vs empty)
        assert ring.push(b"m3") is False

        assert ring.pop() == b"m1"
        assert ring.push(b"m3") is True
        assert ring.qsize() == 2

        assert ring.pop() == b"m2"
        assert ring.pop() == b"m3"
        assert ring.pop() is None
    finally:
        ring.close()
        ring.unlink()


def test_shm_ringbuffer_payload_size_validation():
    buffer_name = "test_gossipmesh_shm_size"
    try:
        temp_buf = SharedMemoryRingBuffer(name=buffer_name, create=False)
        temp_buf.close()
        temp_buf.unlink()
    except Exception:
        pass

    ring = SharedMemoryRingBuffer(name=buffer_name, capacity=4, max_msg_size=10, create=True)
    try:
        with pytest.raises(ValueError):
            ring.push(b"this-payload-is-too-long-exceeding-max-size")
    finally:
        ring.close()
        ring.unlink()
