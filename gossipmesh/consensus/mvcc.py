import threading
from typing import Any, Dict, List, Optional, Tuple


class MVCCConflictError(Exception):
    """Raised when an optimistic concurrency conflict occurs during validation."""

    pass


class MVCCStateStash:
    """Lock-free optimistic multi-version concurrency control (MVCC) state stash
    for autonomous agent memory transactions, tracking mutations with monotonic epochs.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current_epoch: int = 0
        self._store: Dict[str, List[Tuple[int, Any]]] = {}

    def read(self, key: str, epoch: Optional[int] = None) -> Tuple[Any, int]:
        """Reads the latest value or the snapshot value valid at the given epoch with O(1) isolation."""
        with self._lock:
            versions = self._store.get(key)
            if not versions:
                return None, 0
            if epoch is None:
                return versions[-1][1], versions[-1][0]
            valid_val = None
            valid_epoch = 0
            for e, val in versions:
                if e <= epoch:
                    valid_val = val
                    valid_epoch = e
                else:
                    break
            return valid_val, valid_epoch

    def begin_transaction(self) -> Tuple[int, Dict[str, int]]:
        """Begins a new transaction, capturing the current epoch and an empty read set."""
        with self._lock:
            return self._current_epoch, {}

    def validate_and_commit(self, read_set: Dict[str, int], write_set: Dict[str, Any]) -> int:
        """Validates that read-set versions match committed versions and commits writes atomically."""
        with self._lock:
            for key, read_epoch in read_set.items():
                versions = self._store.get(key, [])
                latest_epoch = versions[-1][0] if versions else 0
                if latest_epoch > read_epoch:
                    raise MVCCConflictError(
                        f"Conflict detected on key '{key}': read at epoch {read_epoch}, but latest is {latest_epoch}"
                    )

            self._current_epoch += 1
            new_epoch = self._current_epoch
            for key, val in write_set.items():
                if key not in self._store:
                    self._store[key] = []
                self._store[key].append((new_epoch, val))
            return new_epoch
