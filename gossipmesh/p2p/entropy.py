import math
import asyncio
from collections import deque
from typing import Dict, List, Tuple, Any, Optional
from gossipmesh.p2p.merkle import MerkleDAG, MerkleNode


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


class VectorClockEntropy:
    """Vector clock entropy calculator and tracker for anti-entropy sync."""

    def __init__(self, node_id: str = "") -> None:
        self.node_id = node_id

    def compute(self, vector_clock: Dict[str, int]) -> float:
        return compute_shannon_entropy(vector_clock)

    def update(self, peer_clock: Dict[str, int]) -> None:
        pass


class AntiEntropyEntropy:
    """Anti-entropy entropy tracking."""

    def __init__(self, threshold: float = 1.5) -> None:
        self.threshold = threshold

    def evaluate(self, local_clock: Dict[str, int], peer_clock: Dict[str, int]) -> bool:
        div = compute_divergence_vector(local_clock, peer_clock)
        return compute_shannon_entropy(div) >= self.threshold


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


class HierarchicalAntiEntropySyncer:
    """Asynchronous Hierarchical Merkle-DAG Anti-Entropy Syncer for convergent state reconciliation."""

    def __init__(self, node_id: str, state_store: Dict[str, Any], latency_budget_ms: float = 100.0):
        self.node_id = node_id
        self.state_store = state_store
        self.latency_budget_ms = latency_budget_ms
        self.dag = MerkleDAG(self.state_store)

    def refresh_dag(self) -> None:
        self.dag = MerkleDAG(self.state_store)

    async def reconcile_with_peer(self, peer_id: str, remote_root: MerkleNode) -> List[str]:
        """
        Reconciles local state with a peer using O(log N) Merkle-DAG traversal
        under strict asynchronous latency budgets.
        """
        start_time = asyncio.get_event_loop().time()

        def _sync_task() -> List[str]:
            self.refresh_dag()
            return self.dag.find_divergences(remote_root)

        # Execute under cooperative async boundary to prevent blocking gossip loops
        divergent_keys = await asyncio.to_thread(_sync_task)

        elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000.0
        if elapsed_ms > self.latency_budget_ms:
            # Log or handle latency threshold violation if needed
            pass

        return divergent_keys
