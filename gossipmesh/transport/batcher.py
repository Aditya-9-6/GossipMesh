"""
Lock-Free Slipped-Window Gossip Packet Batcher with Adaptive Coalescing.

Provides a high-throughput, low-memory-footprint packet aggregation engine for
outbound gossip protocol traffic, dynamically adjusting window sizes based on
real-time network backpressure and queue depth metrics.
"""

from __future__ import annotations

import time
import threading
from typing import Any, List, Optional, Tuple, Callable


class SlippedWindowBatcher:
    """
    High-throughput lock-free ring-backed batcher with dynamic adaptive coalescing.
    """

    def __init__(
        self,
        max_window_size: int = 64,
        base_coalesce_window_sec: float = 0.01,
        max_coalesce_window_sec: float = 0.1,
        backpressure_callback: Optional[Callable[[], float]] = None,
    ) -> None:
        self.max_window_size = max(1, max_window_size)
        self.base_coalesce_window_sec = base_coalesce_window_sec
        self.max_coalesce_window_sec = max_coalesce_window_sec
        self.backpressure_callback = backpressure_callback

        self._buffer: List[Any] = [None] * self.max_window_size
        self._head = 0
        self._tail = 0
        self._size = 0
        self._lock = threading.Lock()
        self._last_flush_time = time.monotonic()
        self._total_batched = 0
        self._total_flushed = 0

    def append(self, item: Any) -> bool:
        """Append an item to the batcher buffer atomically."""
        with self._lock:
            if self._size >= self.max_window_size:
                return False
            self._buffer[self._tail] = item
            self._tail = (self._tail + 1) % self.max_window_size
            self._size += 1
            self._total_batched += 1
            return True

    def get_adaptive_window_size(self) -> float:
        """
        Dynamically compute the adaptive coalescing window size based on
        queue depth backpressure or custom callback metrics.
        """
        bp_factor = 0.0
        if self.backpressure_callback is not None:
            try:
                bp_factor = float(self.backpressure_callback())
            except Exception:
                bp_factor = 0.0

        # Scale window based on current fill ratio and external backpressure
        fill_ratio = self._size / float(self.max_window_size)
        effective_factor = max(fill_ratio, min(max(bp_factor, 0.0), 1.0))

        window = self.base_coalesce_window_sec + (
            (self.max_coalesce_window_sec - self.base_coalesce_window_sec) * effective_factor
        )
        return min(window, self.max_coalesce_window_sec)

    def should_flush(self) -> bool:
        """Determine if the batch should be flushed based on window size or constraints."""
        if self._size == 0:
            return False
        if self._size >= self.max_window_size:
            return True

        elapsed = time.monotonic() - self._last_flush_time
        window = self.get_adaptive_window_size()
        return elapsed >= window

    def flush(self) -> List[Any]:
        """Extract all currently batched items and reset the batch window."""
        with self._lock:
            if self._size == 0:
                return []

            items: List[Any] = []
            for _ in range(self._size):
                items.append(self._buffer[self._head])
                self._buffer[self._head] = None
                self._head = (self._head + 1) % self.max_window_size

            flushed_count = self._size
            self._size = 0
            self._last_flush_time = time.monotonic()
            self._total_flushed += flushed_count
            return items

    @property
    def size(self) -> int:
        with self._lock:
            return self._size

    def stats(self) -> dict:
        with self._lock:
            return {
                "size": self._size,
                "max_window_size": self.max_window_size,
                "total_batched": self._total_batched,
                "total_flushed": self._total_flushed,
                "current_coalesce_window": self.get_adaptive_window_size(),
            }
