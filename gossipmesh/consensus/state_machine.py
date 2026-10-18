import json
import hashlib
from typing import Dict, Any, List


class StateMachine:
    """Deterministic key-value state machine supporting log application and state hashing."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._applied_index: int = 0

    def apply(self, command: Dict[str, Any]) -> Any:
        """Apply a command deterministically to the state machine."""
        action = command.get("action")
        key = command.get("key")
        value = command.get("value")

        if action == "SET":
            self._store[key] = value
            result = value
        elif action == "DELETE":
            result = self._store.pop(key, None)
        elif action == "CUSTOM":
            handler_func = command.get("handler")
            if callable(handler_func):
                result = handler_func(self._store, command)
            else:
                result = None
        else:
            result = None

        self._applied_index += 1
        return result

    def get_state_hash(self) -> str:
        """Compute a deterministic SHA-256 hash over sorted keys and values."""
        sorted_items = sorted(self._store.items(), key=lambda x: str(x[0]))
        canonical_repr = json.dumps(sorted_items, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    def get_dump(self) -> Dict[str, Any]:
        return dict(self._store)

    @property
    def applied_index(self) -> int:
        return self._applied_index
