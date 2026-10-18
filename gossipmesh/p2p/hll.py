import math
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import mmh3
except ImportError:
    class _Mmh3Stub:
        @staticmethod
        def hash(key: str, seed: int = 0, signed: bool = True) -> int:
            # Pure Python fallback using FNV-1a / simple hash mix for testing environments without mmh3 C-extension
            h = 2166136261 ^ seed
            for char in str(key):
                h = (h ^ ord(char)) * 16777619
                h &= 0xFFFFFFFF
            if signed and h & 0x80000000:
                return h - 0x100000000
            return h
    mmh3 = _Mmh3Stub()


class WindowedHyperLogLog:
    """Memory-efficient windowed HyperLogLog cardinality estimator using a 1KB bytearray
    of 8-bit registers and a time-decaying sliding window for distributed peer reachability."""

    def __init__(self, num_registers: int = 1024, window_seconds: float = 60.0) -> None:
        self.num_registers = num_registers
        self.window_seconds = window_seconds
        self.p = max(4, min(16, int(math.log2(num_registers))))
        self.m = 1 << self.p
        self.registers = bytearray(self.m)
        self.timestamps = [0.0] * self.m

    def _get_bucket_and_hash(self, item: str) -> Tuple[int, int]:
        h = mmh3.hash(str(item), signed=True)
        if h < 0:
            h += 0x100000000
        idx = h & (self.m - 1)
        remaining = h >> self.p
        return idx, remaining

    def _rho(self, val: int) -> int:
        if val == 0:
            return 32 - self.p
        return min(32 - self.p, (val & -val).bit_length())

    def add(self, item: str, current_time: Optional[float] = None) -> None:
        now = current_time if current_time is not None else time.time()
        idx, remaining = self._get_bucket_and_hash(item)
        rank = self._rho(remaining)

        # Check expiration of existing register
        if now - self.timestamps[idx] > self.window_seconds:
            self.registers[idx] = 0
            self.timestamps[idx] = now

        if rank > self.registers[idx]:
            self.registers[idx] = rank
            self.timestamps[idx] = now

    def estimate(self, current_time: Optional[float] = None) -> int:
        now = current_time if current_time is not None else time.time()
        m = self.m
        
        # Apply time decay / expiration
        valid_registers = []
        for i in range(m):
            if now - self.timestamps[i] <= self.window_seconds:
                valid_registers.append(self.registers[i])
            else:
                valid_registers.append(0)

        if not any(valid_registers):
            return 0

        alpha = 0.7213 / (1.0 + 1.079 / m)
        raw_sum = sum(2.0 ** (-r) for r in valid_registers)
        if raw_sum == 0:
            return 0
            
        estimate = alpha * (m ** 2) / raw_sum

        # Small range correction
        if estimate <= 2.5 * m:
            zeros = valid_registers.count(0)
            if zeros > 0:
                estimate = m * math.log(m / zeros)

        return int(round(estimate))

    def merge(self, other: 'WindowedHyperLogLog', current_time: Optional[float] = None) -> None:
        now = current_time if current_time is not None else time.time()
        for i in range(min(self.m, other.m)):
            other_active = (now - other.timestamps[i] <= other.window_seconds)
            other_val = other.registers[i] if other_active else 0
            
            self_active = (now - self.timestamps[i] <= self.window_seconds)
            self_val = self.registers[i] if self_active else 0

            if other_val > self_val:
                self.registers[i] = other_val
                self.timestamps[i] = other.timestamps[i]

    def get_state(self) -> Dict[str, Any]:
        return {
            "num_registers": self.num_registers,
            "window_seconds": self.window_seconds,
            "registers": list(self.registers),
            "timestamps": self.timestamps,
        }
