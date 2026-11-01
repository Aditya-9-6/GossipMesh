import pytest
import threading
import time
from gossipmesh.p2p.multiplexer import AtomicRingBufferMultiplexer


def test_multiplexer_initialization():
    mux = AtomicRingBufferMultiplexer(capacity=16, max_payload_size=256)
    assert mux.size() == 0
    assert mux.is_empty() is True
    assert mux.is_full() is False


def test_invalid_capacity():
    with pytest.raises(ValueError, match="Capacity must be a power of 2"):
        AtomicRingBufferMultiplexer(capacity=10, max_payload_size=256)


def test_push_pop_single():
    mux = AtomicRingBufferMultiplexer(capacity=4, max_payload_size=128)
    payload = b"agent-gossip-packet-alpha"

    success = mux.push(payload)
    assert success is True
    assert mux.size() == 1
    assert mux.is_empty() is False

    item = mux.pop()
    assert item is not None
    ts, received_payload = item
    assert received_payload == payload
    assert isinstance(ts, int)
    assert mux.size() == 0
    assert mux.is_empty() is True


def test_ring_buffer_overflow():
    mux = AtomicRingBufferMultiplexer(capacity=2, max_payload_size=64)

    assert mux.push(b"msg1") is True
    assert mux.push(b"msg2") is True
    # Ring buffer capacity is 2, so 3rd push should fail (overflow protection)
    assert mux.push(b"msg3") is False

    assert mux.size() == 2
    assert mux.is_full() is True

    assert mux.pop() == (mux._get_head() - 2 >= 0 and any, b"msg1")[1] or mux.pop()[1] == b"msg1"
    assert mux.is_full() is False
    assert mux.push(b"msg3") is True

    # Drain remaining
    _, p2 = mux.pop()
    _, p3 = mux.pop()
    assert p2 == b"msg2"
    assert p3 == b"msg3"
    assert mux.is_empty() is True


def test_payload_size_validation():
    mux = AtomicRingBufferMultiplexer(capacity=4, max_payload_size=8)
    with pytest.raises(ValueError, match="exceeds max_payload_size"):
        mux.push(b"too-long-payload-for-cell")


def test_concurrent_spsc_stress():
    mux = AtomicRingBufferMultiplexer(capacity=1024, max_payload_size=256)
    total_messages = 5000
    produced = []
    consumed = []

    def producer():
        for i in range(total_messages):
            msg = f"gossip-{i}".encode()
            while not mux.push(msg):
                time.sleep(0.0001)

    def consumer():
        count = 0
        while count < total_messages:
            item = mux.pop()
            if item is not None:
                _, payload = item
                consumed.append(payload)
                count += 1
            else:
                time.sleep(0.0001)

    t_prod = threading.Thread(target=producer)
    t_cons = threading.Thread(target=consumer)

    t_prod.start()
    t_cons.start()

    t_prod.join(timeout=5.0)
    t_cons.join(timeout=5.0)

    assert len(consumed) == total_messages
    for i in range(total_messages):
        assert consumed[i] == f"gossip-{i}".encode()
