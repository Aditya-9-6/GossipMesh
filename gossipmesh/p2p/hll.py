import math
import time
import threading
from typing import Optional

try:
    import mmh3
except ImportError:
    mmh3 = None

class _FallbackMurmur3:
    @staticmethod
    def hash(key: str, seed: int = 0, signed: bool = True) -> int:
        h = hash((key, seed))
        if signed:
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
            val = mmh3.hash64(item, seed=self.seed, signed=False)[0]
            return val & 0xFFFFFFFFFFFFFFFF
        else:
            return abs(_FallbackMurmur3.hash(item, self.seed, signed=False)) & 0xFFFFFFFFFFFFFFFF

    def _slide_window(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for i in range(self.num_registers):
            if self.timestamps[i] > 0.0 and self.timestamps[i] < cutoff:
                self.registers[i] = 0
                self.timestamps[i] = 0.0

    def add(self, item: str, timestamp: Optional[float] = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        h = self._hash(item)
        bits_idx = int(math.log2(self.num_registers))
        idx = h & (self.num_registers - 1)
        
        remaining = h >> bits_idx
        if remaining == 0:
            rho = 64 - bits_idx + 1
        else:
            rho = (remaining & -remaining).bit_length() + 1

        with self._lock:
            self._slide_window(ts)
            if rho > self.registers[idx]:
                self.registers[idx] = rho
                self.timestamps[idx] = ts
            elif rho == self.registers[idx] and (self.timestamps[idx] == 0.0 or ts >= self.timestamps[idx]):
                self.timestamps[idx] = ts

    def count(self, current_time: Optional[float] = None) -> int:
        now = current_time if current_time is not None else time.time()
        with self._lock:
            self._slide_window(now)
            active_registers = [float(val) for val in self.registers]

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
            
            # Apply corrections for small and large range estimations
            if estimate <= 2.5 * m:
                zeros = self.registers.count(0)
                if zeros > 0:
                    estimate = m * math.log(m / zeros)
            elif estimate > (1.0 / 30.0) * (2.0 ** 32):
                estimate = -(2.0 ** 32) * math.log(1.0 - estimate / (2.0 ** 32))

            return int(round(estimate))

    def merge(self, other: 'WindowedHyperLogLog', current_time: Optional[float] = None) -> None:
        now = current_time if current_time is not None else time.time()
        with self._lock:
            self._slide_window(now)
            other._slide_window(now)
            for i in range(self.num_registers):
                if other.registers[i] > self.registers[i]:
                    self.registers[i] = other.registers[i]
                    self.timestamps[i] = other.timestamps[i]
                elif other.registers[i] == self.registers[i]:
                    if other.timestamps[i] > self.timestamps[i]:
                        self.timestamps[i] = other.timestamps[i]
