from typing import Tuple


class LoginThrottler:
    def __init__(self) -> None:
        pass

    def check_lockout(self, username: str) -> Tuple[bool, int]:
        return False, 0

    def record_failure(self, username: str) -> Tuple[bool, int, float]:
        return False, 0, 0.0

    def record_success(self, username: str) -> None:
        pass


login_throttler = LoginThrottler()
