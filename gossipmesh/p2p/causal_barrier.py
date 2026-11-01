import time
import threading
from typing import Dict, Any, List, Tuple, Optional


class CausalBarrierFilter:
    """
    Causal dependency barrier filter utilizing vector clocks to buffer and reorder
    out-of-order incoming gossip messages before application delivery.
    Maintains causal consistency by deferring messages whose vector timestamps exceed
    the local causal frontier until missing predecessors are received or a configurable
    bounded retention timeout expires.
    """

    def __init__(self, node_id: str, retention_timeout: float = 5.0):
        self.node_id = node_id
        self.retention_timeout = retention_timeout
        self._local_frontier: Dict[str, int] = {}
        self._buffer: List[Tuple[float, Dict[str, int], Any]] = []  # (timestamp, vector_clock, message)
        self._lock = threading.Lock()

    def update_frontier(self, clock: Dict[str, int]) -> None:
        """Manually update the local causal frontier with a remote vector clock."""
        with self._lock:
            for node, ts in clock.items():
                if ts > self._local_frontier.get(node, 0):
                    self._local_frontier[node] = ts

    def get_frontier(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._local_frontier)

    def _is_causally_ready(self, msg_clock: Dict[str, int], sender_id: Optional[str] = None) -> bool:
        """
        Checks if a message's vector clock satisfies causal readiness against the local frontier.
        A message from sender S with clock C is ready if:
        1. For the sender node S, C[S] == local_frontier[S] + 1
        2. For all other nodes N != S, C[N] <= local_frontier[N]
        If sender_id is not specified, we check that for all nodes N, C[N] <= local_frontier[N] + (1 if N is sender else 0)
        or generally that all dependencies in C are met by the local frontier.
        """
        for node, ts in msg_clock.items():
            local_ts = self._local_frontier.get(node, 0)
            expected_ts = local_ts + 1 if sender_id and node == sender_id else local_ts
            if sender_id and node == sender_id:
                if ts > local_ts + 1:
                    return False
            else:
                if ts > local_ts:
                    return False
        return True

    def process_message(self, message: Any, msg_clock: Dict[str, int], sender_id: Optional[str] = None) -> List[Any]:
        """
        Process an incoming message with its vector clock.
        Returns a list of messages that are now ready for delivery (including this message
        and any previously buffered messages unblocked by this message).
        """
        with self._lock:
            now = time.time()
            # Add incoming to buffer first
            self._buffer.append((now, msg_clock, message))

            # Clean up expired messages due to retention timeout
            valid_buffer = []
            expired_messages = []
            for entry_time, clock, msg in self._buffer:
                if now - entry_time > self.retention_timeout:
                    expired_messages.append(msg)
                else:
                    valid_buffer.append((entry_time, clock, msg))
            self._buffer = valid_buffer

            # Iteratively drain ready messages from the buffer
            delivered = []
            progress = True
            while progress:
                progress = False
                next_buffer = []
                for entry_time, clock, msg in self._buffer:
                    # Check causality against current local frontier
                    ready = True
                    for node, ts in clock.items():
                        local_ts = self._local_frontier.get(node, 0)
                        if ts > local_ts + 1 or (ts > local_ts and node != sender_id):
                            # Refined causal check: allow if ts <= local_ts or (node is sender and ts == local_ts + 1)
                            # More generally, check if all predecessor constraints are satisfied.
                            pass

                    # Simplified robust check: message is ready if all its clock entries are <= local_frontier + 1 for its respective nodes
                    # Specifically, for every node in clock, clock[node] <= local_frontier[node] + (1 if node is sender else 0)
                    is_ready = True
                    for node, ts in clock.items():
                        allowed_max = self._local_frontier.get(node, 0) + (1 if node == sender_id else 0)
                        if ts > allowed_max:
                            # Also check if it's strictly within the general causal bound
                            if ts > self._local_frontier.get(node, 0):
                                is_ready = False
                                break

                    # Alternative standard check: message can be delivered if all dependencies are <= local_frontier
                    # Let's use strict causal dependency: msg clock <= local_frontier except possibly sender increment.
                    can_deliver = True
                    for node, ts in clock.items():
                        limit = self._local_frontier.get(node, 0)
                        if node == sender_id:
                            limit += 1
                        if ts > limit:
                            can_deliver = False
                            break

                    if can_deliver:
                        delivered.append(msg)
                        progress = True
                        # Update local frontier with this delivered message's clock
                        for node, ts in clock.items():
                            if ts > self._local_frontier.get(node, 0):
                                self._local_frontier[node] = ts
                    else:
                        next_buffer.append((entry_time, clock, msg))
                self._buffer = next_buffer

            # Also deliver expired messages forcefully to prevent deadlocks under packet drops
            for expired in expired_messages:
                delivered.append(expired)

            return delivered
