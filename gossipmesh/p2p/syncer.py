from __future__ import annotations

from typing import Any, Dict, List


class VectorClockEntropy:
    def __init__(self, node_id: str | None = None):
        self.node_id = node_id or ""
        self.clock: dict[str, int] = {}

    def increment(self) -> None:
        if self.node_id:
            self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1

    def sync(self, other_clock: dict[str, int]) -> None:
        for k, v in other_clock.items():
            self.clock[k] = max(self.clock.get(k, 0), v)

    def update(self, other_clock: dict[str, int]) -> None:
        self.sync(other_clock)


class StateSyncer:
    def __init__(self, node_id: str):
        self.entropy = VectorClockEntropy(node_id)

    def get_clock(self) -> dict[str, int]:
        return self.entropy.clock

    def update(self, other_clock: dict[str, int]) -> None:
        self.entropy.sync(other_clock)


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_tracker = VectorClockEntropy(node_id)

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock)
        return True


class Syncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync(self, peer_data: Any) -> None:
        if isinstance(peer_data, dict):
            self.entropy.sync(peer_data)
