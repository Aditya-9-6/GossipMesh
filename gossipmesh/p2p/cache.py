import hashlib
import hmac
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple


class GossipMessageCache:
    """High-performance, bounded-memory LRU message deduplication cache
    with active time-to-live (TTL) eviction and O(1) amortized lookup/insertion.
    """

    def __init__(self, capacity: int = 10000, default_ttl: float = 300.0, key: Optional[bytes] = None):
        if capacity <= 0:
            raise ValueError("Cache capacity must be greater than 0.")
        if default_ttl <= 0:
            raise ValueError("Default TTL must be greater than 0.")
        self.capacity = capacity
        self.default_ttl = default_ttl
        self.key = key or b"gossipmesh-siphash-key-32bytes"
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()

    def _compute_digest(self, message_id: str) -> str:
        """Computes a collision-resistant digest for the message ID."""
        if hasattr(hashlib, "siphash24"):
            h = hashlib.siphash24()
            h.update(message_id.encode("utf-8"))
            return h.hexdigest()
        else:
            # HMAC-SipHash simulation fallback
            return hmac.new(self.key, message_id.encode("utf-8"), hashlib.sha256).hexdigest()

    def _evict_expired(self, current_time: float) -> None:
        """Active TTL eviction of expired cache entries."""
        keys_to_evict = []
        for k, (_, expiry) in self._cache.items():
            if expiry <= current_time:
                keys_to_evict.append(k)
            else:
                # OrderedDict is ordered by insertion/access, so we can stop early if not expired
                break
        for k in keys_to_evict:
            self._cache.pop(k, None)

    def __contains__(self, message_id: str) -> bool:
        digest = self._compute_digest(message_id)
        current_time = time.time()
        self._evict_expired(current_time)
        if digest in self._cache:
            _, expiry = self._cache[digest]
            if expiry > current_time:
                return True
            else:
                self._cache.pop(digest, None)
        return False

    def has(self, message_id: str) -> bool:
        """Check if a message digest is present in the cache without updating LRU order."""
        return message_id in self

    def get(self, message_id: str) -> Optional[Any]:
        """Get message payload or metadata and mark as recently used."""
        digest = self._compute_digest(message_id)
        current_time = time.time()
        self._evict_expired(current_time)
        if digest in self._cache:
            value, expiry = self._cache[digest]
            if expiry > current_time:
                # Move to end to mark as recently used
                self._cache.move_to_end(digest)
                return value
            else:
                self._cache.pop(digest, None)
        return None

    def put(self, message_id: str, value: Any = True, ttl: Optional[float] = None) -> None:
        """Insert or update a message in the cache with LRU eviction when capacity is exceeded."""
        digest = self._compute_digest(message_id)
        current_time = time.time()
        self._evict_expired(current_time)

        ttl_val = ttl if ttl is not None else self.default_ttl
        if ttl_val <= 0:
            raise ValueError("TTL must be greater than 0.")
        expiry = current_time + ttl_val

        if digest in self._cache:
            self._cache.move_to_end(digest)
            self._cache[digest] = (value, expiry)
            return

        if len(self._cache) >= self.capacity:
            # Evict the oldest item (first item in OrderedDict)
            self._cache.popitem(last=False)

        self._cache[digest] = (value, expiry)

    def __len__(self) -> int:
        current_time = time.time()
        self._evict_expired(current_time)
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()
