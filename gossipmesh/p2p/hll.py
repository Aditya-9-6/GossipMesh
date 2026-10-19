import math
<<<<<<< HEAD
import time
import threading
from typing import Optional
=======
import threading
import time
from typing import Optional, List, Union
>>>>>>> origin/main

try:
    import mmh3
except ImportError:
    mmh3 = None

<<<<<<< HEAD
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
=======
class WindowedHyperLogLog:
    """Memory-efficient windowed HyperLogLog cardinality estimator
    using fixed 8-bit registers within a 1KB bytearray, strict O(1) insertion,
    and time-decaying sliding windows."""
    
    def __init__(self, num_registers: int = 1024, window_ttl: float = 300.0) -> None:
        if num_registers < 16 or (num_registers & (num_registers - 1)) != 0:
            raise ValueError("Number of registers must be a power of 2 and at least 16")
        
        self.num_registers = num_registers
        self.window_ttl = window_ttl
        self.p = int(math.log2(num_registers))
>>>>>>> origin/main
        self.registers = bytearray(num_registers)
        self.timestamps = [0.0] * num_registers
        self._lock = threading.Lock()

    def _hash(self, item: str) -> int:
        if mmh3 is not None:
<<<<<<< HEAD
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
=======
            # mmh3 returns signed 32-bit int, convert to unsigned 64-bit via hash or standard mmh3 hash64
            try:
                h = mmh3.hash64(item, signed=False)[0]
                return int(h)
            except Exception:
                h = mmh3.hash(item, signed=False)
                return int(h) & 0xFFFFFFFFFFFFFFFF
        else:
            # Fallback pure python hash if mmh3 is not installed in test environment
            return hash(item) & 0xFFFFFFFFFFFFFFFF

    def _rho(self, val: int, max_bits: int = 64) -> int:
        if val == 0:
            return max_bits + 1
        return max_bits - val.bit_length() + 1

    def add(self, item: Union[str, bytes], current_time: Optional[float] = None) -> None:
        if not isinstance(item, (str, bytes)):
            raise TypeError("Item must be str or bytes")
        
        if isinstance(item, str):
            item_bytes = item.encode('utf-8')
        else:
            item_bytes = item
            
        t = current_time if current_time is not None else time.time()
        h = self._hash(item_bytes if isinstance(item, str) else item.decode('utf-8', errors='ignore'))
        
        idx = h & (self.num_registers - 1)
        w_val = h >> self.p
        leading_zeros = self._rho(w_val, 64 - self.p)
        reg_val = min(255, leading_zeros + 1)

        with self._lock:
            self._decay_register(idx, t)
            if reg_val > self.registers[idx]:
                self.registers[idx] = reg_val
                self.timestamps[idx] = t

    def _decay_register(self, idx: int, current_time: float) -> None:
        if self.timestamps[idx] > 0 and (current_time - self.timestamps[idx]) > self.window_ttl:
            self.registers[idx] = 0
            self.timestamps[idx] = 0.0

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
>>>>>>> origin/main
            if m == 16:
                alpha = 0.673
            elif m == 32:
                alpha = 0.697
            elif m == 64:
                alpha = 0.709
            else:
                alpha = 0.7213 / (1.0 + 1.079 / m)
<<<<<<< HEAD

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
=======
                
            raw_sum = 0.0
            zero_count = 0
            for val in self.registers:
                if val == 0:
                    zero_count += 1
                    raw_sum += 1.0
                else:
                    raw_sum += 2.0 ** (-val)
                    
            estimate = alpha * (m * m) / raw_sum
            
            # Small range correction (LinearCounting)
            if estimate <= 2.5 * m and zero_count > 0:
                estimate = m * math.log(m / zero_count)
                
            return float(estimate)

    def merge(self, other: 'WindowedHyperLogLog') -> None:
        if not isinstance(other, WindowedHyperLogLog):
            raise TypeError("Can only merge with another WindowedHyperLogLog")
        if self.num_registers != other.num_registers:
            raise ValueError("Cannot merge estimators with differing register counts")
            
        with self._lock, other._lock:
            t = time.time()
            for i in range(self.num_registers):
                self._decay_register(i, t)
                other._decay_register(i, t)
                
                if other.registers[i] > self.registers[i]:
                    self.registers[i] = other.registers[i]
                    self.timestamps[i] = other.timestamps[i]
>>>>>>> origin/main
