class RedisClientStub:
    def get(self, key: str) -> None:
        return None

    def exists(self, key: str) -> bool:
        return False


redis_client = RedisClientStub()
