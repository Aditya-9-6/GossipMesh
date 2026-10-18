import math

class AdaptiveTTLEngine:
    """Calculates adaptive epidemic Time-To-Live (TTL) decay based on local queue depths
    and downstream neighbor latency, incorporating a congestion-aware poison-reverse heuristic."""

    def __init__(self, base_ttl: int = 10, max_queue_depth: int = 100, max_latency_ms: float = 500.0):
        if max_queue_depth <= 0:
            raise ValueError("max_queue_depth must be greater than zero")
        if max_latency_ms <= 0.0:
            raise ValueError("max_latency_ms must be greater than zero")
        self.base_ttl = base_ttl
        self.max_queue_depth = max_queue_depth
        self.max_latency_ms = max_latency_ms

    def calculate_decay(self, current_ttl: int, queue_depth: int, latency_ms: float, is_poison_reverse: bool = False) -> int:
        """Computes the adjusted TTL given local congestion metrics and poison-reverse flags.
        Functions strictly within single-responsibility constraints and < 50 LOC.
        """
        if is_poison_reverse or current_ttl <= 0:
            return 0

        # Normalized congestion factor (0.0 to 1.0)
        q_factor = min(1.0, max(0.0, queue_depth / float(self.max_queue_depth)))
        l_factor = min(1.0, max(0.0, latency_ms / self.max_latency_ms))

        # Combined penalty score
        congestion_penalty = (q_factor + l_factor) / 2.0

        # Decay formula: reduce TTL faster under higher congestion
        decay_amount = max(1, math.ceil(congestion_penalty * 4.0))
        new_ttl = current_ttl - decay_amount

        return max(0, new_ttl)
