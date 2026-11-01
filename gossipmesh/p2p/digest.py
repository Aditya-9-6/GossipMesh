"""P2P Digest cache and HyperLogLog cardinality estimator."""

import math
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional


class HyperLogLogDigest:
    """HyperLogLog cardinality estimator digest for gossip state reconciliation."""

    def __init__(self, p: int = 14) -> None:
        self.p = p
        self.m = 1 << p
        self.registers = [0] * self.m
        self.alpha = self._get_alpha(self.m)

    def _get_alpha(self, m: int) -> float:
        if m == 16:
            return 0.673
        elif m == 32:
            return 0.697
        elif m == 64:
            return 0.709
        else:
            return 0.7213 / (1.0 + 1.079 / m)

    def _hash(self, item: str) -> int:
        import zlib

        return zlib.crc32(item.encode("utf-8")) & 0xFFFFFFFF

    def add(self, item: str) -> None:
        h = self._hash(item)
        idx = h >> (32 - self.p)
        rho = self._rho(h & ((1 << (32 - self.p)) - 1), 32 - self.p)
        if rho > self.registers[idx]:
            self.registers[idx] = rho

    def _rho(self, val: int, max_bits: int) -> int:
        if val == 0:
            return max_bits + 1
        res = 1
        while (val & (1 << (max_bits - 1))) == 0:
            res += 1
            val <<= 1
        return res

    def count(self) -> float:
        raw_sum = sum(2.0 ** (-r) for r in self.registers)
        estimate = self.alpha * (self.m**2) / raw_sum
        if estimate <= 2.5 * self.m:
            zeros = self.registers.count(0)
            if zeros > 0:
                estimate = self.m * math.log(self.m / zeros)
        return float(estimate)


class LruDigestCache:
    """Thread-safe LRU cache with TTL expiry for gossip message digests."""

    def __init__(self, capacity: int = 1024, default_ttl: float = 60.0) -> None:
        self.capacity = max(16, capacity)
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def _evict_expired_locked(self, now: float) -> None:
        expired_keys = [k for k, (_, exp) in self._cache.items() if exp is not None and exp <= now]
        for k in expired_keys:
            self._cache.pop(k, None)

    def add(self, key: str, value: Any, ttl: Optional[float] = None, now: Optional[float] = None) -> None:
        import time

        timestamp = time.monotonic() if now is None else now
        expiry = timestamp + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._evict_expired_locked(timestamp)
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, expiry)
            if len(self._cache) > self.capacity:
                self._cache.popitem(last=False)

    def get(self, key: str, now: Optional[float] = None) -> Optional[Any]:
        import time

        timestamp = time.monotonic() if now is None else now
        with self._lock:
            self._evict_expired_locked(timestamp)
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key][0]

    def contains(self, key: str, now: Optional[float] = None) -> bool:
        import time

        timestamp = time.monotonic() if now is None else now
        with self._lock:
            self._evict_expired_locked(timestamp)
            return key in self._cache

    def get_size(self, now: Optional[float] = None) -> int:
        import time

        timestamp = time.monotonic() if now is None else now
        with self._lock:
            self._evict_expired_locked(timestamp)
            return len(self._cache)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
