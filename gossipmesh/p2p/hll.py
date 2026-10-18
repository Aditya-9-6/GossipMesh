import math
import time
import threading
from typing import Optional, List

try:
    import mmh3
except ImportError:
    mmh3 = None

class _FallbackMurmur3:
    @staticmethod
    def hash(key: str, seed: int = 0, signed: bool = True) -> int:
        # Simple fallback hash using Python's hash and seed
        h = hash((key, seed))
        if signed:
            # Fit into 32-bit signed integer range
            return ((h + 0x80000000) % 0x100000000) - 0x80000000
        else:
            return h % 0x100000000

class WindowedHyperLogLog:
    """Memory-efficient windowed HyperLogLog (HLL) cardinality estimator
    tracking unique peer reachability across distributed gossip paths.
    Uses fixed 8-bit registers within a 1KB bytearray with O(1) insertion.
    """
    def __init__(self, num_registers: int = 1024, window_seconds: float = 300.0, seed: int = 42) -> None:
        self.num_registers = num_registers
        self.window_seconds = window_seconds
        self.seed = seed
        self.registers = bytearray(num_registers)
        self.timestamps = [0.0] * num_registers
        self._lock = threading.Lock()

    def _hash(self, item: str) -> int:
        if mmh3 is not None:
            return mmh3.hash(item, self.seed, signed=True)
        else:
            return _FallbackMurmur3.hash(item, self.seed, signed=True)

    def add(self, item: str, timestamp: Optional[float] = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        h = self._hash(item)
        # Use lower bits for register index
        bits_idx = int(math.log2(self.num_registers))
        idx = h & (self.num_registers - 1)
        
        # Remaining bits for leading zeros calculation
        remaining = h >> bits_idx
        # Count leading zeros in the remaining bits
        if remaining == 0:
            rho = 32 - bits_idx
        else:
            rho = 1
            while (remaining & 1) == 0 and rho < 32:
                rho += 1
                remaining >>= 1

        with self._lock:
            if ts >= self.timestamps[idx]:
                if rho > self.registers[idx]:
                    self.registers[idx] = rho
                self.timestamps[idx] = ts

    def count(self, current_time: Optional[float] = None) -> int:
        now = current_time if current_time is not None else time.time()
        with self._lock:
            # Apply window decay
            active_registers = []
            for i in range(self.num_registers):
                if now - self.timestamps[i] <= self.window_seconds:
                    active_registers.append(float(self.registers[i]))
                else:
                    active_registers.append(0.0)

            m = float(self.num_registers)
            if m == 16:
                alpha = 0.673
            elif m == 32:
                alpha = 0.697
            elif m == 64:
                alpha = 0.709
            else:
                alpha = 0.7213 / (1.0 + 1.079 / m)

            raw_sum = sum(2.0 ** (-val) for val in active_registers)
            if raw_sum == 0.0:
                return 0

            estimate = alpha * (m ** 2) / raw_sum
            return int(round(estimate))

    def merge(self, other: 'WindowedHyperLogLog', current_time: Optional[float] = None) -> None:
        now = current_time if current_time is not None else time.time()
        with self._lock:
            for i in range(self.num_registers):
                if other.timestamps[i] > self.timestamps[i]:
                    if other.registers[i] > self.registers[i]:
                        self.registers[i] = other.registers[i]
                    self.timestamps[i] = other.timestamps[i]
