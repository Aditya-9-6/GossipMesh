import math

try:
    import mmh3
except ImportError:
    mmh3 = None


class BloomFilterLayer:
    def __init__(self, capacity: int, error_rate: float):
        self.capacity = capacity
        self.error_rate = error_rate
        self.bits = [False] * (capacity * 8)

    def _hashes(self, item: str):
        if mmh3:
            h1 = mmh3.hash(item, 42)
            h2 = mmh3.hash(item, 24)
        else:
            h1 = hash(item)
            h2 = hash(item[::-1])
        return [abs(h1 + i * h2) % len(self.bits) for i in range(3)]

    def add(self, item: str) -> None:
        for h in self._hashes(item):
            self.bits[h] = True

    def __contains__(self, item: str) -> bool:
        return all(self.bits[h] for h in self._hashes(item))


class ScalableBloomRoutingTable:
    def __init__(self, initial_capacity: int = 100, error_rate: float = 0.01, scaling_factor: int = 2):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.scaling_factor = scaling_factor
        self.layers = [BloomFilterLayer(initial_capacity, error_rate)]
        self.total_nodes = 0

    def add(self, item: str) -> None:
        if item in self:
            return
        self.layers[-1].add(item)
        self.total_nodes += 1
        if self.total_nodes >= self.layers[-1].capacity:
            new_cap = self.layers[-1].capacity * self.scaling_factor
            self.layers.append(BloomFilterLayer(new_cap, self.error_rate * 0.5))

    def __contains__(self, item: str) -> bool:
        return any(item in layer for layer in self.layers)

    @property
    def layer_count(self) -> int:
        return len(self.layers)
