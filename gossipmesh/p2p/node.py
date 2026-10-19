import os
import json
import time
import uuid
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Set, Deque
from gossipmesh.p2p.pow import mine_pow, verify_pow


class GossipTopic(str, Enum):
    AGENT_SPAWN = "agent:spawn"
    CODE_REVIEW = "code:review"
    BUILD_STATUS = "build:status"
    SECURITY_ALERT = "security:alert"
    HEARTBEAT = "heartbeat"
    CUSTOM = "custom"


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
            "topic": self.topic,
            "origin_node": self.origin_node,
            "payload": self.payload,
            "repo": self.repo,
            "message_id": self.message_id,
            "vector_clock": self.vector_clock,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GossipMessage":
        return cls(
            topic=data.get("topic", GossipTopic.CUSTOM),
            origin_node=data.get("origin_node", "unknown"),
            payload=data.get("payload", {}),
            repo=data.get("repo", "global"),
            message_id=data.get("message_id"),
            vector_clock=data.get("vector_clock", {}),
            timestamp=data.get("timestamp"),
            ttl=data.get("ttl", 10),
        )


class GossipNode:
    """Decentralized Gossip Peer Node with Proof-of-Work Sybil Deterrence."""

    def __init__(
        self,
        node_id: str,
        mesh_dir: str | None = None,
        public_key: Optional[str] = None,
        pow_difficulty: int = 0,
        pow_nonce: Optional[int] = None,
    ):
        self.node_id = node_id
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path(".gossip_mesh_ledger")
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.public_key = public_key or str(uuid.uuid4())
        self.pow_difficulty = pow_difficulty

        if pow_nonce is not None:
            self.pow_nonce = pow_nonce
            if pow_difficulty > 0 and not verify_pow(self.public_key, self.pow_nonce, self.pow_difficulty):
                raise ValueError("Provided PoW nonce is invalid for the given difficulty and public key")
        elif pow_difficulty > 0:
            self.pow_nonce, _ = mine_pow(self.public_key, pow_difficulty)
        else:
            self.pow_nonce = 0

        self.subscribers: Dict[str, List[Callable[[GossipMessage], None]]] = {}
        self.seen_messages: Set[str] = set()
        self.recent_messages: Deque[GossipMessage] = deque(maxlen=1000)
        self._load_seen_history()

    def _load_seen_history(self):
        if not self.mesh_dir.exists():
            return
        for file_path in self.mesh_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "message_id" in data:
                        self.seen_messages.add(data["message_id"])
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
        self.recent_messages.append(msg)
        self.seen_messages.add(msg.message_id)

        file_path = self.mesh_dir / f"{msg.message_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(msg.to_dict(), f)
        except Exception as e:
            print(f"Error writing message to ledger: {e}")

        return msg

    def sync(self) -> List[GossipMessage]:
        new_messages: List[GossipMessage] = []
        if not self.mesh_dir.exists():
            return new_messages

        for file_path in self.mesh_dir.glob("*.json"):
            if file_path.stem in self.seen_messages:
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    msg = GossipMessage.from_dict(data)
                    if msg.message_id not in self.seen_messages:
                        self.seen_messages.add(msg.message_id)
                        self.recent_messages.append(msg)
                        new_messages.append(msg)
                        self._dispatch_to_subscribers(msg)
            except Exception:
                continue
        return new_messages

    def _dispatch_to_subscribers(self, msg: GossipMessage):
        handlers = self.subscribers.get(msg.topic, [])
        for handler in handlers:
            try:
                handler(msg)
            except Exception as e:
                print(f"Subscriber error on topic {msg.topic}: {e}")

    def heartbeat(self):
        self.publish(GossipTopic.HEARTBEAT, {"status": "alive", "timestamp": time.time(), "pow_nonce": self.pow_nonce})

    def get_recent_messages(self, topic: Optional[GossipTopic] = None, limit: int = 50) -> List[GossipMessage]:
        msgs = list(self.recent_messages)
        if topic:
            msgs = [m for m in msgs if m.topic == topic]
        return msgs[-limit:]

    def cleanup_ledger(self):
        if not self.mesh_dir.exists():
            return
        now = time.time()
        for file_path in self.mesh_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    timestamp = data.get("timestamp", now)
                    ttl = data.get("ttl", 10)
                    if (now - timestamp) > (ttl * 60):
                        file_path.unlink(missing_ok=True)
            except Exception:
                continue
