from typing import Dict, Any, List, Optional
from gossipmesh.p2p.digest import HyperLogLogDigest


class GossipDigestCompactor:
    """Memory-bounded gossip digest compactor using HyperLogLog sketches for anti-entropy sync."""

    def __init__(self, precision: int = 12) -> None:
        self.precision = precision
        self.hll = HyperLogLogDigest(precision=precision)

    def add_peer_state(self, item_id: str) -> None:
        """Add a peer state identifier or hash to the compaction sketch."""
        self.hll.add(item_id)

    def compact(self) -> Dict[str, Any]:
        """Compact peer state digest into a sub-linear payload (<1KB)."""
        return self.hll.serialize()

    @classmethod
    def reconcile(cls, local_compactor: "GossipDigestCompactor", remote_digest_data: Dict[str, Any]) -> float:
        """Reconcile local state with remote HLL digest data, returning estimated union cardinality."""
        remote_hll = HyperLogLogDigest.deserialize(remote_digest_data)
        local_compactor.hll.merge(remote_hll)
        return local_compactor.hll.cardinality
