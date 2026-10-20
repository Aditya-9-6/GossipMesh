from typing import Any, Dict, Optional
from gossipmesh.p2p.entropy import AntiEntropyEngine


class PeerStateSyncer:
    """Synchronizes peer state using anti-entropy engine."""

    def __init__(self, engine: AntiEntropyEngine) -> None:
        self.engine = engine

    def synchronize(self, remote_state: Dict[str, Any]) -> Dict[str, Any]:
        return self.engine.compare_state(remote_state)
