from typing import Tuple, Any, Optional


class P2PTransport:
    def __init__(self):
        pass

    def get_endpoint(self) -> Tuple[str, int]:
        return ("127.0.0.1", 8080)
