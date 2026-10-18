from typing import Optional
from gossipmesh.p2p.dedup import CompressedBloomFilter

class GossipTransport:
    """P2P transport layer incorporating compressed Bloom filter message deduplication."""
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01):
        self.dedup_filter = CompressedBloomFilter(capacity=capacity, error_rate=error_rate)

    def should_process_message(self, message_id: str) -> bool:
        """Checks if a message ID has been seen before. If not, records it and returns True atomically."""
        return self.dedup_filter.check_and_add(message_id)

    def reset_dedup(self) -> None:
        self.dedup_filter.clear()
