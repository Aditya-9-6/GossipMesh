import threading
import time
import pytest
from gossipmesh.p2p.spsc_mux import SpscAtoMicRingBufferMultiplexer


def test_spsc_mux_basic_operations():
    mux = SpscAtoMicRingBufferMultiplexer(capacity=4, max_payload_size=64)
    assert mux.is_empty
    assert len(mux) == 0

    assert mux.push(b"ping-1") is True
    assert mux.push(b"ping-2") is True
    assert len(mux) == 2
    assert not mux.is_empty

    ts1, payload1 = mux.pop()
    assert payload1 == b"ping-1"
    assert isinstance(ts1, int)

    ts2, payload2 = mux.pop()
    assert payload2 == b"ping-2"
    assert mux.is_empty

    assert mux.pop() is None


def test_spsc_mux_capacity_and_overflow():
    mux = SpscAtoMicRingBufferMultiplexer(capacity=2, max_payload_size=32)
    assert mux.push(b"msg-1") is True
    assert mux.push(b"msg-2") is True
    assert mux.is_full is True

    # Should reject when full
    assert mux.push(b"msg-3") is False

    _, p1 = mux.pop()
    assert p1 == b"msg-1"
    assert mux.is_full is False

    assert mux.push(b"msg-3") is True
    _, p2 = mux.pop()
    assert p2 == b"msg-2"
    _, p3 = mux.pop()
    assert p3 == b"msg-3"
    assert mux.is_empty


def test_spsc_mux_invalid_capacity():
    with pytest.raises(ValueError, match="Capacity must be a power of 2"):
        SpscAtoMicRingBufferMultiplexer(capacity=3)


def test_spsc_mux_payload_size_limit():
    mux = SpscAtoMicRingBufferMultiplexer(capacity=4, max_payload_size=8)
    with pytest.raises(ValueError, match="exceeds max_payload_size"):
        mux.push(b"this-payload-is-too-long")


def test_spsc_mux_concurrent_stress():
    capacity = 1024
    mux = SpscAtoMicRingBufferMultiplexer(capacity=capacity, max_payload_size=256)
    num_messages = 5000

    produced = []
    consumed = []

    def producer_worker():
        for i in range(num_messages):
            msg = f"agent-beat-{i}".encode()
            while not mux.push(msg):
                time.sleep(0.0001)
            produced.append(msg)

    def consumer_worker():
        count = 0
        while count < num_messages:
            item = mux.pop()
            if item is not None:
                _, payload = item
                consumed.append(payload)
                count += 1
            else:
                time.sleep(0.0001)

    p_thread = threading.Thread(target=producer_worker)
    c_thread = threading.Thread(target=consumer_worker)

    p_thread.start()
    c_thread.start()

    p_thread.join(timeout=5.0)
    c_thread.join(timeout=5.0)

    assert len(produced) == num_messages
    assert len(consumed) == num_messages
    assert produced == consumed
    assert mux.is_empty
