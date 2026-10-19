<<<<<<< HEAD
import hashlib
import json
from typing import Dict, List, Tuple, Any

class MerkleIntervalNode:
    def __init__(self, start_key: str, end_key: str, digest: str):
        self.start_key = start_key
        self.end_key = end_key
        self.digest = digest

class VectorClockEntropyEngine:
    @staticmethod
    def data_hasher(d: Any) -> str:
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode("utf-8")).hexdigest()

    @classmethod
    def compute_digest(cls, items: Dict[str, Any]) -> str:
        if not items:
            return hashlib.sha256(b"").hexdigest()
        return cls.data_hasher(items)

    @classmethod
    def build_merkle_tree(cls, state_store: Dict[str, Any], bucket_size: int = 16) -> List[MerkleIntervalNode]:
        sorted_keys = sorted(state_store.keys())
        if not sorted_keys:
            return [MerkleIntervalNode("", "", cls.compute_digest({}))]
        nodes = []
        for i in range(0, len(sorted_keys), bucket_size):
            bucket_keys = sorted_keys[i:i + bucket_size]
            bucket_data = {k: state_store[k] for k in bucket_keys}
            digest = cls.compute_digest(bucket_data)
            nodes.append(MerkleIntervalNode(bucket_keys[0], bucket_keys[-1], digest))
        return nodes

    @staticmethod
    def compare_clocks(clock_a: Dict[str, int], clock_b: Dict[str, int]) -> str:
        keys = set(clock_a.keys()).union(set(clock_b.keys()))
        greater = False
        lesser = False
        for k in keys:
            va = clock_a.get(k, 0)
            vb = clock_b.get(k, 0)
            if va > vb:
                greater = True
            elif va < vb:
                lesser = True
        if greater and not lesser:
            return "after"
        if lesser and not greater:
            return "before"
        if not greater and not lesser:
            return "equal"
        return "concurrent"

    @classmethod
    def reconcile_state(cls, local_state: Dict[str, Any], local_clock: Dict[str, int], peer_state: Dict[str, Any], peer_clock: Dict[str, int]) -> Tuple[Dict[str, Any], Dict[str, int]]:
        relation = cls.compare_clocks(local_clock, peer_clock)
        if relation == "after":
            return local_state, local_clock
        if relation == "before":
            return peer_state, peer_clock
        merged_state = {**peer_state, **local_state}
        merged_clock = {k: max(local_clock.get(k, 0), peer_clock.get(k, 0)) for k in set(local_clock).union(peer_clock)}
        return merged_state, merged_clock
=======
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
    def __init__(self, node_id: str = 'node-1', entropy_threshold: float = 1.5, buffer_capacity: int = 100):
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
>>>>>>> origin/main
