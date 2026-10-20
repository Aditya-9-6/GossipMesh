import time
import json
import hashlib
import threading
from typing import Dict, Any, Optional, Tuple
from gossipmesh.p2p.merkle_trie import MerklePatriciaTree


class StateCheckpointer:
    def __init__(self):
        self.trie = MerklePatriciaTree()
        self._lock = threading.Lock()
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def update_state(self, key: str, value: Any) -> str:
        with self._lock:
            self.trie.insert(key, value)
            return self.trie.get_root_hash()

    def remove_state(self, key: str) -> str:
        with self._lock:
            self.trie.delete(key)
            return self.trie.get_root_hash()

    def create_snapshot(self) -> Tuple[str, float]:
        start_time = time.perf_counter()
        with self._lock:
            root_hash = self.trie.get_root_hash()
            snapshot_data = {"root_hash": root_hash, "store": dict(self.trie.store), "timestamp": time.time()}
            self.snapshots[root_hash] = snapshot_data
        duration = (time.perf_counter() - start_time) * 1000.0
        return root_hash, duration

    def verify_snapshot(self, root_hash: str) -> bool:
        with self._lock:
            if root_hash not in self.snapshots:
                return False
            snap = self.snapshots[root_hash]
            temp_trie = MerklePatriciaTree()
            for k, v in snap["store"].items():
                temp_trie.insert(k, v)
            return temp_trie.get_root_hash() == root_hash

    def restore_snapshot(self, root_hash: str) -> bool:
        with self._lock:
            if root_hash not in self.snapshots:
                return False
            snap = self.snapshots[root_hash]
            self.trie = MerklePatriciaTree()
            for k, v in snap["store"].items():
                self.trie.insert(k, v)
            return True
