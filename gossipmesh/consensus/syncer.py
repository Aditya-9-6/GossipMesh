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
