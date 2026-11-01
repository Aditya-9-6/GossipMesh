from typing import Any


class HyperLogLogDigest:
    def __init__(self):
        pass

    def add(self, item: Any) -> None:
        pass

    def serialize(self) -> bytes:
        return b""

    @classmethod
    def deserialize(cls, data: bytes) -> "HyperLogLogDigest":
        return cls()

    def cardinality(self) -> int:
        return 0
