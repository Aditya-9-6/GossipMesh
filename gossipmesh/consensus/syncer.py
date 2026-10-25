"""
Consensus Syncer using Merkle Trees.
"""

from __future__ import annotations

from typing import Any


class ConsensusSyncer:
    def __init__(self, merkle_tree: Any) -> None:
        self.merkle_tree = merkle_tree

    def get_fingerprints(self) -> list[bytes]:
        if hasattr(self.merkle_tree, "get_fingerprints"):
            fps = self.merkle_tree.get_fingerprints()
            if fps and isinstance(fps[0], str):
                return [str(f).encode() for f in fps]
            return list(fps)
        return []


class MerkleSyncer(ConsensusSyncer):
    """Alias for ConsensusSyncer for Merkle tree synchronization."""

    def get_sync_manifest(self) -> dict[str, str]:
        if hasattr(self.merkle_tree, "items") and isinstance(self.merkle_tree.items, dict):
            return {str(k): str(v) for k, v in self.merkle_tree.items.items()}
        return {}

    def reconcile(self, manifest: dict[str, str]) -> list[str]:
        local = self.get_sync_manifest()
        divergent = []
        for k, v in local.items():
            if manifest.get(k) != v:
                divergent.append(k)
        for k in manifest:
            if k not in local:
                divergent.append(k)
        return divergent

    def generate_delta_payload(self, keys: list[str]) -> dict[str, str]:
        local = self.get_sync_manifest()
        return {k: local[k] for k in keys if k in local}
