import pytest
from gossipmesh.p2p.multiplexer import AtomicRingBufferMultiplexer


def test_multiplexer_power_of_2_validation():
    with pytest.raises(ValueError, match="Capacity must be a power of 2"):
        AtomicRingBufferMultiplexer(capacity=100)


def test_multiplexer_push_pop_happy_path():
    mux = AtomicRingBufferMultiplexer(capacity=4, max_payload_size=64)
    
    assert mux.push(b"hello gossip", priority=1) is True
    assert mux.push(b"consensus sync", priority=8) is True
    
    item1 = mux.pop()
    assert item1 is not None
    prio1, ts1, payload1 = item1
    assert prio1 == 1
    assert payload1 == b"hello gossip"

    item2 = mux.pop()
    assert item2 is not None
    prio2, ts2, payload2 = item2
    assert prio2 == 8
    assert payload2 == b"consensus sync"

    assert mux.pop() is None


def test_multiplexer_priority_shedding():
    mux = AtomicRingBufferMultiplexer(capacity=2, max_payload_size=32)
    
    # Fill buffer
    assert mux.push(b"telemetry 1", priority=1) is True
    assert mux.push(b"telemetry 2", priority=2) is True
    
    # Buffer is full (capacity 2). Pushing low priority should be dropped immediately.
    assert mux.push(b"telemetry 3", priority=1) is False
    
    # Pushing critical consensus (priority 5+) should evict oldest low priority item
    assert mux.push(b"consensus critical", priority=7) is True
    
    # Pop remaining items: telemetry 2 and consensus critical
    _, _, pl1 = mux.pop()
    assert pl1 == b"telemetry 2"
    
    prio_c, _, pl2 = mux.pop()
    assert prio_c == 7
    assert pl2 == b"consensus critical"
