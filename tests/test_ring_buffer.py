import concurrent.futures
import threading
import pytest

from gossipmesh.p2p.ring_buffer import LockFreeDoubleBufferedRingBuffer


def test_ring_buffer_basic_push_pop():
    rb = LockFreeDoubleBufferedRingBuffer(capacity=4, max_msg_size=64)
    assert rb.is_empty
    assert rb.size == 0

    assert rb.has_space if hasattr(rb, 'has_space') else True
    assert rb.push(b"hello") is True
    assert rb.push(b"world") is True
    assert rb.size == 2
    assert not rb.is_empty

    assert rb.pop() == b"hello"
    assert rb.pop() == b"world"
    assert rb.pop() is None
    assert rb.is_empty


def test_ring_buffer_capacity_bounds():
    rb = LockFreeDoubleBufferedRingBuffer(capacity=2, max_msg_size=32)
    assert rb.push(b"one") is True
    assert rb.push(b"two") is True
    assert rb.push(b"three") is False  # Full

    assert rb.pop() == b"one"
    assert rb.push(b"three") is True  # Space available now
    assert rb.pop() == b"two"
    assert rb.pop() == b"three"
    assert rb.pop() is None


def test_ring_buffer_payload_size_validation():
    rb = LockFreeDoubleBufferedRingBuffer(capacity=4, max_msg_size=8)
    with pytest.raises(ValueError):
        rb.push(b"this payload is way too long for max_msg_size")


def test_concurrent_producers_consumers():
    capacity = 256
    rb = LockFreeDoubleBufferedRingBuffer(capacity=capacity, max_msg_size=128)
    num_items = 1000

    def producer(start: int, end: int):
        for i in range(start, end):
            payload = f"msg-{i}".encode('utf-8')
            while not rb.push(payload):
                pass

    consumed = []
    consumed_lock = threading.Lock()

    def consumer(target_count: int):
        while len(consumed) < target_count:
            item = rb.pop()
            if item is not None:
                with consumed_lock:
                    consumed.append(item)
            else:
                pass

    t_prod1 = threading.Thread(target=producer, args=(0, num_items // 2))
    t_prod2 = threading.Thread(target=producer, args=(num_items // 2, num_items))
    t_cons = threading.Thread(target=consumer, args=(num_items,))

    t_cons.start()
    t_prod1.start()
    t_prod2.start()

    t_prod1.join()
    t_prod2.join()
    t_cons.join()

    assert len(consumed) == num_items
    decoded = {msg.decode('utf-8') for msg in consumed}
    expected = {f"msg-{i}" for i in range(num_items)}
    assert decoded == expected
