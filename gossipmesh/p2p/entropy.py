import math
from collections import deque
from typing import Dict, List, Tuple, Any


class VectorClockRingBuffer:
    """Fixed-size bounded memory ring buffer for tracking peer vector clocks."""

    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)

    def push(self, vector_clock: Dict[str, int]) -> None:
        """Pushes a vector clock into the bounded ring buffer."""
        self._buffer.append(dict(vector_clock))

    def get_all(self) -> List[Dict[str, int]]:
        """Returns all stored vector clocks in the buffer."""
        return list(self._buffer)

    def clear(self) -> None:
        """Clears the ring buffer."""
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)


def compute_divergence_vector(local_clock: Dict[str, int], peer_clock: Dict[str, int]) -> Dict[str, int]:
    """Computes absolute element-wise divergence between local and peer vector clocks."""
    all_keys = set(local_clock.keys()).union(set(peer_clock.keys()))
    divergence: Dict[str, int] = {}
    for key in all_keys:
        l_val = local_clock.get(key, 0)
        p_val = peer_clock.get(key, 0)
        divergence[key] = abs(l_val - p_val)
    return divergence


def compute_shannon_entropy(divergence_vector: Dict[str, int]) -> float:
    """Computes Shannon entropy over the divergence vector distribution."""
    if not divergence_vector:
        return 0.0

    total = sum(divergence_vector.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for val in divergence_vector.values():
        if val > 0:
            prob = val / total
            entropy -= prob * math.log2(prob)

    return float(entropy)


class AntiEntropyScraper:
    """Vector-Clock Entropy-Based Anti-Entropy Scraper for mesh peer divergence monitoring."""

    def __init__(self, entropy_threshold: float = 1.5, buffer_capacity: int = 100):
        self.entropy_threshold = entropy_threshold
        self.peer_buffers: Dict[str, VectorClockRingBuffer] = {}
        self.buffer_capacity = buffer_capacity

    def _get_or_create_buffer(self, peer_id: str) -> VectorClockRingBuffer:
        if peer_id not in self.peer_buffers:
            self.peer_buffers[peer_id] = VectorClockRingBuffer(capacity=self.buffer_capacity)
        return self.peer_buffers[peer_id]

    def record_peer_clock(self, peer_id: str, vector_clock: Dict[str, int]) -> None:
        """Records a peer's vector clock observation into its ring buffer."""
        buf = self._get_or_create_buffer(peer_id)
        buf.push(vector_clock)

    def evaluate_peer(self, local_clock: Dict[str, int], peer_id: str) -> Tuple[float, bool]:
        """Evaluates divergence entropy for a peer against the local clock.
        Returns (entropy_value, should_sync_flag).
        """
        buf = self._get_or_create_buffer(peer_id)
        clocks = buf.get_all()
        if not clocks:
            return 0.0, False

        latest_peer_clock = clocks[-1]
        divergence = compute_divergence_vector(local_clock, latest_peer_clock)
        entropy = compute_shannon_entropy(divergence)

        should_sync = entropy >= self.entropy_threshold
        return entropy, should_sync

    def scan_mesh(self, local_clock: Dict[str, int]) -> List[str]:
        """Scans all tracked peers and returns a list of peer IDs requiring state synchronization."""
        sync_peers: List[str] = []
        for peer_id in list(self.peer_buffers.keys()):
            _, should_sync = self.evaluate_peer(local_clock, peer_id)
            if should_sync:
                sync_peers.append(peer_id)
        return sync_peers


class AntiEntropyEngine:
    """Engine supporting both scraper-based divergence and state reconciliation tests."""

    def __init__(self, node_id: str = "node-1", entropy_threshold: float = 1.5, buffer_capacity: int = 100):
        self.node_id = node_id
        self.state_store: Dict[str, Any] = {}
        self.scraper = AntiEntropyScraper(entropy_threshold=entropy_threshold, buffer_capacity=buffer_capacity)

    def set_state(self, key: str, value: Any) -> None:
        self.state_store[key] = value

    def reconcile_divergence(self, peer_state: Dict[str, Any]) -> List[str]:
        diffs = []
        all_keys = set(self.state_store.keys()).union(set(peer_state.keys()))
        for k in all_keys:
            if self.state_store.get(k) != peer_state.get(k):
                diffs.append(k)
        return diffs

    def evaluate_peer(self, local_clock: Dict[str, int], peer_id: str) -> Tuple[float, bool]:
        return self.scraper.evaluate_peer(local_clock, peer_id)

    def record_peer_clock(self, peer_id: str, vector_clock: Dict[str, int]) -> None:
        self.scraper.record_peer_clock(peer_id, vector_clock)

    def scan_mesh(self, local_clock: Dict[str, int]) -> List[str]:
        return self.scraper.scan_mesh(local_clock)
