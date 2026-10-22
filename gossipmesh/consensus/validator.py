import threading
from typing import Dict, Optional, Set
from gossipmesh.consensus.checkpoint import StateCheckpoint


class EpochCheckpointValidator:
    def __init__(self, total_nodes: int, secret_keys: Optional[Dict[str, str]] = None) -> None:
        self.total_nodes = total_nodes
        self.secret_keys = secret_keys or {}
        self._lock = threading.Lock()
        self._checkpoints: Dict[int, Dict[str, StateCheckpoint]] = {}
        self._finalized_epochs: Set[int] = set()
        self._finalized_roots: Dict[int, str] = {}

    def required_quorum(self) -> int:
        return (2 * self.total_nodes // 3) + 1

    def submit_checkpoint(self, checkpoint: StateCheckpoint) -> bool:
        with self._lock:
            if checkpoint.epoch in self._finalized_epochs:
                return False

            if checkpoint.node_id not in self.secret_keys:
                return False
            key = self.secret_keys[checkpoint.node_id]
            if not checkpoint.verify_signature(key):
                return False

            epoch_map = self._checkpoints.setdefault(checkpoint.epoch, {})
            epoch_map[checkpoint.node_id] = checkpoint
            return True

    def check_quorum(self, epoch: int) -> bool:
        with self._lock:
            if epoch in self._finalized_epochs:
                return True
            epoch_map = self._checkpoints.get(epoch, {})

            root_counts: Dict[str, int] = {}
            for cp in epoch_map.values():
                root_counts[cp.state_root] = root_counts.get(cp.state_root, 0) + 1

            quorum = self.required_quorum()
            for root, count in root_counts.items():
                if count >= quorum:
                    self._finalized_epochs.add(epoch)
                    self._finalized_roots[epoch] = root
                    return True
            return False

    def is_finalized(self, epoch: int) -> bool:
        with self._lock:
            return epoch in self._finalized_epochs

    def get_finalized_state_root(self, epoch: int) -> Optional[str]:
        with self._lock:
            return self._finalized_roots.get(epoch)
