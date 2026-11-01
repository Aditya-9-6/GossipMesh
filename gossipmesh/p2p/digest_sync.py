import math
import hashlib
import base64
import threading
from typing import Set, List, Dict, Any, Optional
from gossipmesh.p2p.digest import BloomFilterDigest


class DynamicBloomDigestSync:
    """
    Dynamic Bloom-Filter Digest Synchronization Engine for efficient P2P anti-entropy state exchanges.
    Constructs size-adaptive, hash-optimized Bloom filters representing local node state inventories,
    compressing digest synchronization overhead and supporting automated false-positive rate tuning
    based on peer population metrics.
    """

    def __init__(self, initial_capacity: int = 1000, base_error_rate: float = 0.01) -> None:
        self.capacity = max(1, initial_capacity)
        self.base_error_rate = min(max(0.0001, base_error_rate), 0.5)
        self._lock = threading.Lock()
        self._digest = BloomFilterDigest(capacity=self.capacity, error_rate=self.base_error_rate)
        self._peer_population = 1

    @property
    def capacity_val(self) -> int:
        with self._lock:
            return self.capacity

    @property
    def error_rate(self) -> int:
        with self._lock:
            return self.base_error_rate

    def tune_for_peer_population(self, peer_count: int) -> None:
        """
        Automatically adjusts the false-positive rate and capacity tuning based on active peer population metrics.
        Larger peer groups tighten error tolerance to mitigate false-positive broadcast cascades.
        """
        with self._lock:
            self._peer_population = max(1, peer_count)
            # Scale error rate logarithmically with peer population for optimal bandwidth efficiency
            adjusted_error = max(0.00001, self.base_error_rate / (1.0 + math.log10(self._peer_population)))
            if abs(adjusted_error - self._digest.error_rate) > 1e-6:
                # Re-initialize digest with tuned error rate while retaining current items if feasible
                current_items = getattr(self, "_item_cache", set())
                self._digest = BloomFilterDigest(capacity=self.capacity, error_rate=adjusted_error)
                if not hasattr(self, "_item_cache"):
                    self._item_cache = set()
                for item in self._item_cache:
                    self._digest.add(item)

    def add(self, item: str) -> None:
        with self._lock:
            if not hasattr(self, "_item_cache"):
                self._item_cache = set()
            self._item_cache.add(item)
            # Check if dynamic capacity expansion is required
            if self._digest.element_count >= self.capacity:
                self.capacity = int(self.capacity * 2)
                new_digest = BloomFilterDigest(capacity=self.capacity, error_rate=self._digest.error_rate)
                for cached_item in self._item_cache:
                    new_digest.add(cached_item)
                self._digest = new_digest
            self._digest.add(item)

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    def contains(self, item: str) -> bool:
        with self._lock:
            return item in self._digest

    def reconcile(self, remote_digest_data: Dict[str, Any]) -> List[str]:
        """
        Reconciles local state against a remote node's serialized Bloom filter digest.
        Returns items present in local cache but potentially missing on remote.
        """
        with self._lock:
            if not hasattr(self, "_item_cache"):
                return []
            remote_digest = BloomFilterDigest.deserialize(remote_digest_data)
            missing: List[str] = []
            for item in self._item_cache:
                if item not in remote_digest:
                    missing.append(item)
            return missing

    def serialize(self) -> Dict[str, Any]:
        with self._lock:
            base_ser = self._digest.serialize()
            base_ser["dynamic_capacity"] = self.capacity
            base_ser["peer_population"] = self._peer_population
            return base_ser

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "DynamicBloomDigestSync":
        cap = data.get("dynamic_capacity", data.get("capacity", 1000))
        err = data.get("error_rate", 0.01)
        instance = cls(initial_capacity=cap, base_error_rate=err)
        instance._digest = BloomFilterDigest.deserialize(data)
        instance._peer_population = data.get("peer_population", 1)
        return instance
