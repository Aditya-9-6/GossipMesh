import pytest
import threading
import time
from gossipmesh.p2p.buffer_pool import ZeroCopyBufferPool
from gossipmesh.p2p.multiplexer import AtomicRingBufferMultiplexer


def test_buffer_pool_basic():
    pool = ZeroCopyBufferPool(slice_size=1024, initial_pool_size=4, max_pool_size=16)
    assert pool.available_count == 4
    
    buf = pool.acquire()
    assert len(buf) == 1024
    assert pool.available_count == 3
    
    pool.release(buf)
    assert pool.available_count == 4


def test_multiplexer_push_pop():
    mux = AtomicRingBufferMultiplexer(capacity=4, max_payload_size=256)
    
    assert mux.push(b"hello gossip", priority=1) is True
    assert mux.push(b"consensus vote", priority=10) is True
    
    item1 = mux.pop()
    assert item1 is not None
    prio1, ts1, payload1 = item1
    assert prio1 == 1
    assert payload1 == b"hello gossip"
    
    item2 = mux.pop()
    assert item2 is not None
    prio2, ts2, payload2 = item2
    assert prio2 == 10
    assert payload2 == b"consensus vote"
    
    assert mux.pop() is None


def test_multiplexer_backpressure_and_shedding():
    mux = AtomicRingBufferMultiplexer(capacity=2, max_payload_size=256)
    
    # Fill capacity
    assert mux.push(b"telemetry 1", priority=1) is True
    assert mux.push(b"telemetry 2", priority=2) is True
    
    # Ring is full (capacity 2). Low priority push should be shed / dropped.
    assert mux.push(b"telemetry 3", priority=1) is False
    
    # High priority push (>= 5) should evict oldest low-priority telemetry frame
    assert mux.push(b"consensus critical", priority=8) is True
    
    # Pop remaining items
    item1 = mux.pop()
    assert item1 is not None
    assert item1[0] == 2  # telemetry 2 remains
    assert item1[2] == b"telemetry 2"
    
    item2 = mux.pop()
    assert item2 is not None
    assert item2[0] == 8  # consensus critical inserted
    assert item2[2] == b"consensus critical"
    
    assert mux.pop() is None


def test_multiplexer_concurrent_stress():
    mux = AtomicRingBufferMultiplexer(capacity=128, max_payload_size=512)
    num_messages = 500
    
    def producer():
        for i in range(num_messages):
            prio = 10 if i % 5 == 0 else 1
            while not mux.push(f"msg-{i}".encode(), priority=prio):
                time.sleep(0.0001)
                
    def consumer(results):
        count = 0
        while count < num_messages:
            item = mux.pop()
            if item is not None:
                results.append(item)
                count += 1
            else:
                time.sleep(0.0001)
                
    results = []
    t_prod = threading.Thread(target=producer)
    t_cons = threading.Thread(target=consumer, args=(results,))
    
    t_prod.start()
    t_cons.start()
    
    t_prod.join(timeout=5.0)
    t_cons.join(timeout=5.0)
    
    assert len(results) == num_messages
