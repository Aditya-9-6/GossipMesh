import time


class LoginThrottler:
    def __init__(self):
        self.failures = {}
        self.lockouts = {}

    def check_lockout(self, username: str) -> tuple[bool, int]:
        now = time.time()
        if username in self.lockouts:
            unlock_time = self.lockouts[username]
            if now < unlock_time:
                return True, int(unlock_time - now)
            else:
                del self.lockouts[username]
        return False, 0

    def record_failure(self, username: str) -> tuple[bool, int, int]:
        now = time.time()
        count = self.failures.get(username, 0) + 1
        self.failures[username] = count
        if count >= 5:
            lockout_duration = 300
            self.lockouts[username] = now + lockout_duration
            return True, lockout_duration, 5
        return False, 0, 0


login_throttler = LoginThrottler()
