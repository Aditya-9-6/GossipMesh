import os
import json
import time
import uuid
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from gossipmesh.p2p.churn import EntropyChurnDefense


class GossipTopic(str, Enum):
    CODE_REVIEW = "code_review"
    SECURITY_ALERT = "security_alert"
    AGENT_SYNC = "agent_sync"
    HEARTBEAT = "heartbeat"


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
        self.vector_clock = vector_clock or {}
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
            topic=data.get("topic", GossipTopic.AGENT_SYNC),
            origin_node=data.get("origin_node", "unknown"),
            payload=data.get("payload", {}),
            repo=data.get("repo", "global"),
            message_id=data.get("message_id"),
            vector_clock=data.get("vector_clock", {}),
            timestamp=data.get("timestamp"),
            ttl=data.get("ttl", 10),
        )


class GossipNode:
    """Decentralized Gossip Peer Node with Entropy-Based Churn Defense."""

    def __init__(self, node_id: str, mesh_dir: str | None = None):
        self.node_id = node_id
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path(".gossip_mesh/ledger")
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.subscribers: Dict[str, List[Callable[[GossipMessage], None]]] = {}
        self.seen_messages: set = set()
        self.message_cache: deque = deque(maxlen=1000)
        self.churn_defense = EntropyChurnDefense()
        self._load_seen_history()

    def _load_seen_history(self):
        if not self.mesh_dir.exists():
            return
        for file_path in self.mesh_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    mid = data.get("message_id")
                    if mid:
                        self.seen_messages.add(mid)
            except Exception:
                continue

    def subscribe(self, topic: GossipTopic, handler: Callable[[GossipMessage], None]):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(handler)

    def publish(
        self, topic: GossipTopic, payload: Dict[str, Any], repo: str = "global", ttl: int = 10
    ) -> GossipMessage:
        msg = GossipMessage(topic=topic, origin_node=self.node_id, payload=payload, repo=repo, ttl=ttl)
        self.seen_messages.add(msg.message_id)
        self.message_cache.append(msg)

        ledger_file = self.mesh_dir / f"{msg.message_id}.json"
        with open(ledger_file, "w", encoding="utf-8") as f:
            json.dump(msg.to_dict(), f)

        return msg

    def ingest_message(self, msg: GossipMessage) -> bool:
        """Ingests an incoming peer message, passing metadata to entropy churn defense."""
        if self.churn_defense.is_quarantined(msg.origin_node):
            return False

        feature = float(msg.timestamp % 60)
        self.churn_defense.record_message(msg.origin_node, feature)

        if self.churn_defense.evaluate_peer(msg.origin_node):
            return False

        if msg.message_id in self.seen_messages:
            return False

        self.seen_messages.add(msg.message_id)
        self.message_cache.append(msg)
        return True

    def sync(self) -> List[GossipMessage]:
        new_messages: List[GossipMessage] = []
        if not self.mesh_dir.exists():
            return new_messages

        for file_path in self.mesh_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    msg = GossipMessage.from_dict(data)
                    if msg.origin_node != self.node_id:
                        if self.ingest_message(msg):
                            new_messages.append(msg)
            except Exception:
                continue
        return new_messages

    def heartbeat(self):
        self.publish(GossipTopic.HEARTBEAT, {"status": "alive", "time": time.time()})

    def get_recent_messages(self, topic: Optional[GossipTopic] = None, limit: int = 50) -> List[GossipMessage]:
        msgs = list(self.message_cache)
        if topic:
            msgs = [m for m in msgs if m.topic == topic]
        return msgs[-limit:]

    def cleanup_ledger(self):
        if not self.mesh_dir.exists():
            return
        for file_path in self.mesh_dir.glob("*.json"):
            try:
                file_path.unlink()
            except Exception:
                continue
