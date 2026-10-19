import json
import hashlib
from typing import Dict, Any


class RaftLogCompactionEngine:
    """Manages Raft log truncation and structural state snapshot generation."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.last_included_index = 0
        self.last_included_term = 0
        self.state_tree: Dict[str, Any] = {}

    def apply_entry(self, index: int, term: int, command: Dict[str, Any]) -> None:
        self.state_tree.update(command)
        self.last_included_index = max(self.last_included_index, index)
        self.last_included_term = max(self.last_included_term, term)

    def should_compact(self, log_length: int) -> bool:
        return log_length > self.window_size

    def create_snapshot(self) -> Dict[str, Any]:
        state_bytes = json.dumps(self.state_tree, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(state_bytes).hexdigest()
        return {
            "last_included_index": self.last_included_index,
            "last_included_term": self.last_included_term,
            "state_tree": self.state_tree,
            "checksum": checksum,
        }

    def restore_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.last_included_index = snapshot.get("last_included_index", 0)
        self.last_included_term = snapshot.get("last_included_term", 0)
        self.state_tree = snapshot.get("state_tree", {}).copy()
