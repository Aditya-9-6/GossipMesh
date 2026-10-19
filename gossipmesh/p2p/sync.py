from typing import Set, List, Dict, Any
from gossipmesh.p2p.digest import BloomFilterDigest


class AntiEntropySync:
    """Handles peer state reconciliation via Bloom filter digests."""

    @staticmethod
    def create_node_digest(keys: Set[str], capacity: int = 1000, error_rate: float = 0.01) -> Dict[str, Any]:
        digest = BloomFilterDigest(capacity=capacity, error_rate=error_rate)
        for key in keys:
            digest.add(key)
        return digest.serialize()

    @staticmethod
    def reconcile(local_keys: Set[str], remote_digest_data: Dict[str, Any]) -> List[str]:
        """Reconciles local keys against a remote node's digest, returning items the remote node is missing."""
        remote_digest = BloomFilterDigest.deserialize(remote_digest_data)
        missing_on_remote = []
        for key in local_keys:
            if key not in remote_digest:
                missing_on_remote.append(key)
        return missing_on_remote
