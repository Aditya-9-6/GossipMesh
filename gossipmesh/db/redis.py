class RedisClientStub:
    def get(self, key: str) -> bytes | None:
        return None

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return True

    def exists(self, key: str) -> bool:
        return False

    def delete(self, key: str) -> int:
        return 1


redis_client = RedisClientStub()
