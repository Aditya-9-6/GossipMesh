class LoginThrottler:
    def __init__(self, limit: int = 5, window: int = 60) -> None:
        self.limit = limit
        self.window = window
        self.attempts: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        import time

        now = time.time()
        history = self.attempts.get(key, [])
        history = [t for t in history if now - t < self.window]
        self.attempts[key] = history
        return len(history) < self.limit

    def record(self, key: str) -> None:
        import time

        now = time.time()
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(now)


login_throttler = LoginThrottler()
