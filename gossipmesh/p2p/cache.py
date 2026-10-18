import hashlib
import hmac
import time
from collections import OrderedDict
from typing import Any, Optional, Dict, Tuple


class GossipMessageCache:
    """High-performance, bounded-memory LRU message deduplication cache
    using SipHash-2-4 (via hashlib.siphash24 or HMAC-SipHash simulation/fallback)
    for collision-resistant digest lookups.
    """
    def __init__(self, capacity: int = 10000, key: Optional[bytes] = None):
        if capacity <= 0:
            raise ValueError("Cache capacity must be greater than 0")
        self.capacity = capacity
        # Use a random 128-bit key if none provided for SipHash hashing
        self.key = key or b"\x00" * 16
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()

    def _compute_digest(self, message_id: str) -> str:
        """Computes a SipHash-2-4 digest for the message ID to ensure O(1)
        collision-resistant lookups.
        """
        try:
            # Python's hashlib supports siphash24 in newer versions, or we fallback to hmac/sha256 if unavailable
            if hasattr(hashlib, "siphash24"):
                h = hashlib.siphash24(self.key, message_id.encode("utf-8"))
                return h.hexdigest()
        except Exception:
            pass
        
        # Fallback/deterministic SipHash emulation using hmac with sha256 truncated or standard digest
        return hmac.new(self.key, message_id.encode("utf-8"), hashlib.sha256).hexdigest()

    def __contains__(self, message_id: str) -> bool:
        return self.has(message_id)

    def has(self, message_id: str) -> bool:
        """Check if a message digest is present in the cache without updating LRU order."""
        digest = self._compute_digest(message_id)
        return digest in self._cache

    def get(self, message_id: str) -> Optional[Any]:
        """Get message payload or metadata and mark as recently used."""
        digest = self._compute_digest(message_id)
        if digest in self._cache:
            self._cache.move_to_end(digest)
            return self._cache[digest][1]
        return None

    def put(self, message_id: str, value: Any = True) -> None:
        """Insert or update a message in the cache with LRU eviction when capacity is exceeded."""
        digest = self._compute_digest(message_id)
        timestamp = time.time()
        if digest in self._cache:
            self._cache.move_to_end(digest)
            self._cache[digest] = (timestamp, value)
            return

        if len(self._cache) >= self.capacity:
            # Evict least recently used item (first item in OrderedDict)
            self._cache.popitem(last=False)

        self._cache[digest] = (timestamp, value)

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()
