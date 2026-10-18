import math
import threading
import time
from typing import Optional, List, Union

try:
    import mmh3
except ImportError:
    mmh3 = None

class WindowedHyperLogLog:
    """Memory-efficient windowed HyperLogLog cardinality estimator
    using fixed 8-bit registers within a 1KB bytearray, strict O(1) insertion,
    and time-decaying sliding windows."""
    
    def __init__(self, num_registers: int = 1024, window_seconds: float = 300.0) -> None:
        if num_registers < 16 or (num_registers & (num_registers - 1)) != 0:
            raise ValueError("Number of registers must be a power of 2 and at least 16")
        
        self.num_registers = num_registers
        self.window_ttl = window_seconds
        self.window_seconds = window_seconds
        self.p = int(math.log2(num_registers))
        self.registers = bytearray(num_registers)
        self.timestamps = [0.0] * num_registers
        self._lock = threading.Lock()

    def _hash(self, item: str) -> int:
        if mmh3 is not None:
            try:
                h = mmh3.hash64(item, signed=False)[0]
                return int(h)
            except Exception:
                h = mmh3.hash(item, signed=False)
                return int(h) & 0xFFFFFFFFFFFFFFFF
        else:
            return hash(item) & 0xFFFFFFFFFFFFFFFF

    def _rho(self, val: int, max_bits: int = 64) -> int:
        if val == 0:
            return max_bits + 1
        return max_bits - val.bit_length() + 1

    def add(self, item: Union[str, bytes], timestamp: Optional[float] = None, current_time: Optional[float] = None) -> None:
        if not isinstance(item, (str, bytes)):
            raise TypeError("Item must be str or bytes")
        
        if isinstance(item, str):
            item_bytes = item.encode('utf-8')
        else:
            item_bytes = item
            
        t = timestamp if timestamp is not None else (current_time if current_time is not None else time.time())
        h = self._hash(item_bytes.decode('utf-8', errors='ignore'))
        
        idx = h >> (64 - self.p)
        remaining_bits = h & ((1 << (64 - self.p)) - 1)
        
        leading_zeros = 1
        mask = 1 << (63 - self.p)
        while mask > 0 and (remaining_bits & mask) == 0:
            leading_zeros += 1
            mask >>= 1
            
        rank = min(255, leading_zeros)

        with self._lock:
            self._decay_register(idx, t)
            if rank > self.registers[idx]:
                self.registers[idx] = rank
                self.timestamps[idx] = t

    def _decay_register(self, idx: int, current_time: float) -> None:
        if self.timestamps[idx] > 0 and (current_time - self.timestamps[idx]) > self.window_ttl:
            self.registers[idx] = 0
            self.timestamps[idx] = 0.0

    def decay(self, current_time: Optional[float] = None) -> None:
        t = current_time if current_time is not None else time.time()
        with self._lock:
            for i in range(self.num_registers):
                self._decay_register(i, t)

    def estimate(self, current_time: Optional[float] = None) -> float:
        t = current_time if current_time is not None else time.time()
        with self._lock:
            self.decay(t)
            m = self.num_registers
            
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
                raw_sum += 2.0 ** (-val)
                
            est = alpha * (m * m) / raw_sum
            
            if est <= 2.5 * m and zero_count > 0:
                est = m * math.log(m / zero_count)
                
            return float(est)

    def count(self, current_time: Optional[float] = None) -> float:
        return self.estimate(current_time=current_time)

    def merge(self, other: 'WindowedHyperLogLog', current_time: Optional[float] = None) -> None:
        if not isinstance(other, WindowedHyperLogLog):
            raise TypeError("Can only merge with another WindowedHyperLogLog")
        if self.num_registers != other.num_registers:
            raise ValueError("Cannot merge estimators with differing register counts")
            
        t = current_time if current_time is not None else time.time()
        with self._lock, other._lock:
            self.decay(t)
            other.decay(t)
            for i in range(self.num_registers):
                if other.registers[i] > self.registers[i]:
                    self.registers[i] = other.registers[i]
                    self.timestamps[i] = other.timestamps[i]
