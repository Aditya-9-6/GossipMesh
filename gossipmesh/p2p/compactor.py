from typing import List
from gossipmesh.p2p.digest import HyperLogLogDigest


class GossipDigestCompactor:
    """Compacts node state IDs into HLL digests and computes Jaccard-like distance diffs."""

    def __init__(self, precision: int = 12):
        self.precision = precision

    def compact_state(self, item_ids: List[str]) -> HyperLogLogDigest:
        hll = HyperLogLogDigest(precision=self.precision)
        for item_id in item_ids:
            hll.add(item_id)
        return hll

    def compute_diff(self, local_digest: HyperLogLogDigest, remote_digest: HyperLogLogDigest) -> float:
        merged = local_digest.merge(remote_digest)
        est_local = local_digest.estimate_cardinality()
        est_remote = remote_digest.estimate_cardinality()
        est_merged = merged.estimate_cardinality()

        if est_merged == 0:
            return 0.0

        intersection = max(0.0, est_local + est_remote - est_merged)
        union = est_merged
        jaccard_similarity = intersection / union if union > 0 else 1.0
        return float(1.0 - jaccard_similarity)

    def serialize_digest(self, digest: HyperLogLogDigest) -> str:
        return digest.serialize()

    def deserialize_digest(self, data_str: str) -> HyperLogLogDigest:
        return HyperLogLogDigest.deserialize(data_str)
