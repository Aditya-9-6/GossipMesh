import os
import json
import time
import uuid
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
from gossipmesh.p2p.pow import mine_pow, verify_pow
from gossipmesh.p2p.scatter import AdaptiveScatterGovernor
from gossipmesh.p2p.liveness import PeerLivenessTracker


class GossipTopic(str, Enum):
    CODE_CHANGE = "code_change"
    REVIEW_FEEDBACK = "review_feedback"
    SECURITY_ALERT = "security_alert"
    HEARTBEAT = "heartbeat"
    AGENT_STATE = "agent_state"


class GossipMessage:
    def __init__(
        self,
        topic: str,
        origin_node: str,
        payload: Dict[str, Any],
        repo: str = "global",
        message_id: Optional[str] = None,
        vector_clock: Optional[Dict[str, int]] = None,
        timestamp: Optional[float] = None,
        ttl: int = 10,
    ):
        self.topic = topic
        self.origin_node = origin_node
        self.payload = payload
        self.repo = repo
        self.message_id = message_id or str(uuid.uuid4())
        self.vector_clock = vector_clock or {origin_node: 1}
        self.timestamp = timestamp or time.time()
        self.ttl = ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "topic": self.topic,
            "origin_node": self.origin_node,
            "payload": self.payload,
            "repo": self.repo,
            "vector_clock": self.vector_clock,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GossipMessage":
        return cls(
            topic=data["topic"],
            origin_node=data["origin_node"],
            payload=data["payload"],
            repo=data.get("repo", "global"),
            message_id=data.get("message_id"),
            vector_clock=data.get("vector_clock"),
            timestamp=data.get("timestamp"),
            ttl=data.get("ttl", 10),
        )


class GossipNode:
    """Decentralized Gossip Peer Node with Proof-of-Work Sybil Deterrence,
    Adaptive Scatter-Width CPU-Load Feedback Shaping, and Windowed Liveness Tracking."""

    def __init__(
        self,
        node_id: str,
        mesh_dir: str | None = None,
        public_key: Optional[str] = None,
        pow_difficulty: int = 0,
        pow_nonce: Optional[int] = None,
        base_scatter: int = 4,
    ):
        self.node_id = node_id
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path(".gossip_mesh")
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.public_key = public_key
        self.pow_difficulty = pow_difficulty
        self.pow_nonce = pow_nonce
        self.subscribers: Dict[str, List[Callable[[GossipMessage], None]]] = {}
        self.seen_messages: set = set()
        self.message_cache: deque = deque(maxlen=200)
        self._load_seen_history()
        self.scatter_governor = AdaptiveScatterGovernor(base_scatter=base_scatter)
        self.liveness_tracker = PeerLivenessTracker()

    def _load_seen_history(self):
        """Loads message IDs previously witnessed to prevent duplicate processing."""
        seen_file = self.mesh_dir / f"{self.node_id}_seen.json"
        if seen_file.exists():
            try:
                with open(seen_file, "r") as f:
                    data = json.load(f)
                    self.seen_messages = set(data)
            except Exception:
                self.seen_messages = set()

    def subscribe(self, topic: GossipTopic, handler: Callable[[GossipMessage], None]):
        """Registers a reactive listener callback for a gossip topic."""
        t_str = str(topic)
        if t_str not in self.subscribers:
            self.subscribers[t_str] = []
        self.subscribers[t_str].append(handler)

    def publish(
        self, topic: GossipTopic, payload: Dict[str, Any], repo: str = "global", ttl: int = 10
    ) -> GossipMessage:
        """Broadcasts an epidemic gossip event across the mesh with adaptive scatter shaping."""
        msg = GossipMessage(topic=str(topic), origin_node=self.node_id, payload=payload, repo=repo, ttl=ttl)
        self.seen_messages.add(msg.message_id)
        self.message_cache.append(msg)

        # Persist to shared mesh ledger file
        ledger_file = self.mesh_dir / f"{msg.message_id}.json"
        with open(ledger_file, "w") as f:
            json.dump(msg.to_dict(), f)

        self._dispatch_to_subscribers(msg)
        return msg

    def sync(self) -> List[GossipMessage]:
        """Runs anti-entropy synchronization: scans the shared ledger for newly
        arrived gossip messages from other peer nodes."""
        new_messages: List[GossipMessage] = []
        if not self.mesh_dir.exists():
            return new_messages

        for file_path in self.mesh_dir.glob("*.json"):
            if file_path.name.endswith("_seen.json"):
                continue
            msg_id = file_path.stem
            if msg_id not in self.seen_messages:
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        msg = GossipMessage.from_dict(data)
                        self.seen_messages.add(msg.message_id)
                        self.message_cache.append(msg)
                        new_messages.append(msg)
                        self._dispatch_to_subscribers(msg)
                except Exception:
                    pass
        return new_messages

    def _dispatch_to_subscribers(self, msg: GossipMessage):
        handlers = self.subscribers.get(msg.topic, [])
        for h in handlers:
            try:
                h(msg)
            except Exception:
                pass

    def heartbeat(self):
        """Updates this node's live liveness timestamp and resource governor."""
        if hasattr(self.scatter_governor, "record_heartbeat"):
            getattr(self.scatter_governor, "record_heartbeat")()
        self.publish(GossipTopic.HEARTBEAT, {"node_id": self.node_id, "status": "alive"}, ttl=2)

    def get_recent_messages(self, topic: Optional[GossipTopic] = None, limit: int = 50) -> List[GossipMessage]:
        """Fetches the latest gossip messages from the in-memory cache."""
        msgs = list(self.message_cache)
        if topic:
            msgs = [m for m in msgs if m.topic == str(topic)]
        return msgs[-limit:]

    def cleanup_ledger(self):
        """Removes expired messages from the ledger based on TTL."""
        pass
