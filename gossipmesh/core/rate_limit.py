import time
from typing import Any, Optional


class RedisPipelineStub:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def incr(self, key: str) -> "RedisPipelineStub":
        self.commands.append(("incr", (key,), {}))
        return self

    def expire(self, key: str, seconds: int) -> "RedisPipelineStub":
        self.commands.append(("expire", (key, seconds), {}))
        return self

    def execute(self) -> list[Any]:
        return [1 for _ in self.commands]


class RedisClientStub:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> Optional[bytes]:
        val = self._store.get(key)
        if val is not None:
            if isinstance(val, bytes):
                return val
            return str(val).encode("utf-8")
        return None

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    def incr(self, key: str) -> int:
        current = int(self._store.get(key, 0))
        current += 1
        self._store[key] = current
        return current

    def expire(self, key: str, seconds: int) -> bool:
        return True

    def pipeline(self) -> RedisPipelineStub:
        return RedisPipelineStub()
