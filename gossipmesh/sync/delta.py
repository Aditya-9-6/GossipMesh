from __future__ import annotations
import asyncio
from typing import Dict, Any, List, Set, Tuple
from gossipmesh.sync.vector_clock import VectorClock


class DeltaSyncEngine:
    def __init__(self, node_id: str, max_causal_entries: int = 100) -> None:
        self.node_id = node_id
        self.max_causal_entries = max_causal_entries
        self.local_clock = VectorClock()
        self.state_store: Dict[str, Tuple[Any, VectorClock]] = {}
        self._lock = asyncio.Lock()

    async def update_state(self, key: str, value: Any) -> VectorClock:
        async with self._lock:
            self.local_clock.increment(self.node_id)
            self.local_clock.compact(max_entries=self.max_causal_entries)
            vc_copy = VectorClock(self.local_clock.to_dict())
            self.state_store[key] = (value, vc_copy)
            return vc_copy

    async def get_delta(self, remote_clock_dict: Dict[str, int]) -> Dict[str, Any]:
        remote_vc = VectorClock.from_dict(remote_clock_dict)
        delta: Dict[str, Any] = {}
        async with self._lock:
            for key, (val, val_vc) in self.state_store.items():
                comp = val_vc.compare(remote_vc)
                if comp in ("AFTER", "CONCURRENT"):
                    delta[key] = {"value": val, "vector_clock": val_vc.to_dict()}
        return delta

    async def merge_delta(self, remote_delta: Dict[str, Dict[str, Any]]) -> List[str]:
        merged_keys = []
        async with self._lock:
            for key, entry in remote_delta.items():
                remote_val = entry.get("value")
                remote_vc = VectorClock.from_dict(entry.get("vector_clock", {}))

                if key not in self.state_store:
                    self.state_store[key] = (remote_val, remote_vc)
                    merged_keys.append(key)
                else:
                    local_val, local_vc = self.state_store[key]
                    comp = remote_vc.compare(local_vc)
                    if comp == "AFTER":
                        self.state_store[key] = (remote_val, remote_vc)
                        merged_keys.append(key)
                    elif comp == "CONCURRENT":
                        # Last-write-wins fallback or deterministic merge strategy
                        self.state_store[key] = (remote_val, remote_vc)
                        merged_keys.append(key)

                # Merge clocks
                for k, v in remote_vc.clock.items():
                    self.local_clock.clock[k] = max(self.local_clock.clock.get(k, 0), v)
            self.local_clock.compact(max_entries=self.max_causal_entries)
        return merged_keys

    async def compute_delta_concurrent(self, remote_clock_dict: Dict[str, int]) -> Dict[str, Any]:
        """Computes minimal delta payloads concurrently without blocking the primary event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: asyncio.run(self.get_delta(remote_clock_dict)))
