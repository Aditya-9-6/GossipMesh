import time
import pytest
from gossipmesh.transport.batcher import SlippedWindowBatcher


def test_batcher_basic_append_and_flush():
    batcher = SlippedWindowBatcher(max_window_size=5)
    assert batcher.size == 0

    assert batcher.append("msg1") is True
    assert batcher.append("msg2") is True
    assert batcher.size == 2

    items = batcher.flush()
    assert items == ["msg1", "msg2"]
    assert batcher.size == 0
    assert batcher.flush() == []


def test_batcher_capacity_limit():
    batcher = SlippedWindowBatcher(max_window_size=2)
    assert batcher.append("a") is True
    assert batcher.append("b") is True
    assert batcher.append("c") is False  # Over capacity
    assert batcher.size == 2

    items = batcher.flush()
    assert items == ["a", "b"]
    assert batcher.append("c") is True
    assert batcher.size == 1


def test_adaptive_coalescing_window():
    # Test with custom backpressure callback returning high backpressure
    batcher = SlippedWindowBatcher(
        max_window_size=10,
        base_coalesce_window_sec=0.01,
        max_coalesce_window_sec=0.2,
        backpressure_callback=lambda: 1.0,
    )
    window = batcher.get_adaptive_window_size()
    assert window == 0.2

    # Test zero backpressure with empty queue
    batcher2 = SlippedWindowBatcher(
        max_window_size=10,
        base_coalesce_window_sec=0.01,
        max_coalesce_window_sec=0.2,
        backpressure_callback=lambda: 0.0,
    )
    assert batcher2.get_adaptive_window_size() == 0.01


def test_should_flush_logic():
    batcher = SlippedWindowBatcher(max_window_size=5, base_coalesce_window_sec=0.001)
    assert batcher.should_flush() is False

    batcher.append("test")
    # Wait for coalescing window to elapse
    time.sleep(0.005)
    assert batcher.should_flush() is True

    # Reaching max window size should trigger flush regardless of timer
    batcher_full = SlippedWindowBatcher(max_window_size=2)
    batcher_full.append(1)
    batcher_full.append(2)
    assert batcher_full.should_flush() is True
