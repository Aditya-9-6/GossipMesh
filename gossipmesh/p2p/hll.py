import math
import threading
import time
from typing import List, Optional, Union

try:
    import mmh3
except ImportError:
    mmh3 = None


class _FallbackMurmur3:
    @staticmethod
    def hash(key: Union[str, bytes], seed: int = 0, signed: bool = True) -> int:
        h = hash((key, seed))
        if signed:
            return ((h + 0x80000000) % 0x100000000) - 0x80000000
        else:
            return h % 0x100000000


class WindowedHyperLogLog:
    """Memory-efficient windowed HyperLogLog (HLL) cardinality estimator
    tracking unique peer reachability across distributed gossip paths.
    Uses fixed 8-bit registers within a 1KB bytearray, strict O(1) insertion,
    and time-decaying sliding windows.
    """

    def __init__(
        self,
        num_registers: int = 1024,
        window_ttl: float = 300.0,
        seed: int = 42,
        window_seconds: Optional[float] = None,
    ) -> None:
        if num_registers < 16 or (num_registers & (num_registers - 1)) != 0:
            raise ValueError("Number of registers must be a power of 2 and at least 16")

        ttl = window_seconds if window_seconds is not None else window_ttl
        self.num_registers = num_registers
        self.window_ttl = ttl
        self.window_seconds = ttl
        self.seed = seed
        self.p = int(math.log2(num_registers))
        self.registers = bytearray(num_registers)
        self.timestamps = [0.0] * num_registers
        self._lock = threading.RLock()

    def _hash(self, item: Union[str, bytes]) -> int:
        if mmh3 is not None:
            # mmh3 returns signed 32-bit int, convert to unsigned 64-bit via hash or standard mmh3 hash64
            try:
                val = mmh3.hash64(item, seed=self.seed, signed=False)[0]
                return int(val) & 0xFFFFFFFFFFFFFFFF
            except TypeError:
                try:
                    val = mmh3.hash64(item, signed=False)[0]
                    return int(val) & 0xFFFFFFFFFFFFFFFF
                except Exception:
                    val = mmh3.hash(item, signed=False)
                    return int(val) & 0xFFFFFFFFFFFFFFFF
            except Exception:
                val = mmh3.hash(item, signed=False)
                return int(val) & 0xFFFFFFFFFFFFFFFF
        else:
            # Fallback pure python hash if mmh3 is not installed in test environment
            if isinstance(item, bytes):
                item_str = item.decode('utf-8', errors='replace')
            else:
                item_str = item
            return abs(_FallbackMurmur3.hash(item_str, self.seed, signed=False)) & 0xFFFFFFFFFFFFFFFF

    def _rho(self, val: int, max_bits: int = 64) -> int:
        if val == 0:
            return max_bits + 1
        return max_bits - val.bit_length() + 1

    def add(
        self,
        item: Union[str, bytes],
        timestamp: Optional[float] = None,
        current_time: Optional[float] = None,
    ) -> None:
        if not isinstance(item, (str, bytes)):
            raise TypeError("Item must be str or bytes")

        t = timestamp if timestamp is not None else (current_time if current_time is not None else time.time())
        h = self._hash(item)

        idx = h & (self.num_registers - 1)
        w_val = h >> self.p
        leading_zeros = self._rho(w_val, 64 - self.p)
        reg_val = min(255, leading_zeros + 1)

        with self._lock:
            self._decay_register(idx, t)
            if reg_val > self.registers[idx]:
                self.registers[idx] = reg_val
                self.timestamps[idx] = t
            elif reg_val == self.registers[idx] and (self.timestamps[idx] == 0.0 or t >= self.timestamps[idx]):
                self.timestamps[idx] = t

    def _decay_register(self, idx: int, current_time: float) -> None:
        if self.timestamps[idx] > 0 and (current_time - self.timestamps[idx]) > self.window_ttl:
            self.registers[idx] = 0
            self.timestamps[idx] = 0.0

    def _slide_window(self, now: float) -> None:
        for i in range(self.num_registers):
            self._decay_register(i, now)

    def decay(self, current_time: float) -> None:
        with self._lock:
            for i in range(self.num_registers):
                self._decay_register(i, current_time)

    def estimate(self, current_time: Optional[float] = None) -> float:
        t = current_time if current_time is not None else time.time()
        with self._lock:
            self.decay(t)
            m = self.num_registers

            # Alpha constant determination
            if m == 16:
                alpha = 0.673
            elif m == 32:
                alpha = 0.697
            elif m == 64:
                alpha = 0.709
            else:
                alpha = 0.7213 / (1.0 + 1.079 / m)

            raw_sum = 0.0
            zero_count = 0
            for val in self.registers:
                if val == 0:
                    zero_count += 1
                    raw_sum += 1.0
                else:
                    raw_sum += 2.0 ** (-val)

            if raw_sum == 0.0:
                return 0.0

            estimate = alpha * (m * m) / raw_sum

            # Small and large range corrections
            if estimate <= 2.5 * m and zero_count > 0:
                estimate = m * math.log(m / zero_count)
            elif estimate > (1.0 / 30.0) * (2.0 ** 32):
                estimate = -(2.0 ** 32) * math.log(1.0 - estimate / (2.0 ** 32))

            return float(estimate)

    def count(self, current_time: Optional[float] = None) -> int:
        return int(round(self.estimate(current_time)))

    def merge(self, other: 'WindowedHyperLogLog', current_time: Optional[float] = None) -> None:
        if not isinstance(other, WindowedHyperLogLog):
            raise TypeError("Can only merge with another WindowedHyperLogLog")
        if self.num_registers != other.num_registers:
            raise ValueError("Cannot merge estimators with differing register counts")

        t = current_time if current_time is not None else time.time()
        with self._lock, other._lock:
            for i in range(self.num_registers):
                self._decay_register(i, t)
                other._decay_register(i, t)

                if other.registers[i] > self.registers[i]:
                    self.registers[i] = other.registers[i]
                    self.timestamps[i] = other.timestamps[i]
                elif other.registers[i] == self.registers[i]:
                    if other.timestamps[i] > self.timestamps[i]:
                        self.timestamps[i] = other.timestamps[i]
