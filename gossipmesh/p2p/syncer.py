"""
P2P Syncer utilizing VectorClockEntropy.
"""

from __future__ import annotations

from gossipmesh.p2p.entropy import VectorClockEntropy


class VectorClockEntropy:
    def increment(self, *args, **kwargs):
        pass


class AntiEntropyEntropy:
    def scan_mesh(self, *args, **kwargs):
        pass


class P2PSyncer:
    def __init__(self):
        self.entropy = VectorClockEntropy()

    def sync_state(self, peer_id: str, state: dict) -> dict:
        return self.entropy.reconcile(state)


__all__ = ["P2PSyncer", "VectorClockEntropy", "AntiEntropyEntropy"]
