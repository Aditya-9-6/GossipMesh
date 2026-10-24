import os
import json
import time
import uuid
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Set
from gossipmesh.p2p.pow import mine_pow, verify_pow
from gossipmesh.p2p.scatter import AdaptiveScatterGovernor


class GossipTopic(str, Enum):
    AGENT_EVENT = "agent_event"
    CODE_REVIEW = "code_review"
    CONSENSUS = "consensus"
    HEARTBEAT = "heartbeat"
    TASK_BID = "task_bid"


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
    def from_dict(cls, data: Dict[str, Any]) -> 'GossipMessage':
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
    """Decentralized Gossip Peer Node with Proof-of-Work Sybil Deterrence
    and Adaptive Scatter-Width CPU-Load Feedback Shaping.
    Communicates via a shared ledger directory (file-backed mesh) or local bus."""
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
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path(".gossip_mesh/ledger")
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.public_key = public_key
        self.pow_difficulty = pow_difficulty
        self.pow_nonce = pow_nonce
        self.subscribers: Dict[str, List[Callable[[GossipMessage], None]]] = {}
        self.seen_messages: Set[str] = set()
        self.recent_messages: deque = deque(maxlen=200)
        self._load_seen_history()
        self.scatter_governor = AdaptiveScatterGovernor(base_scatter=base_scatter)

    def _load_seen_history(self):
        """Loads message IDs previously witnessed to prevent duplicate processing."""
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
        """Registers a reactive listener callback for a gossip topic."""
        topic_str = topic.value if isinstance(topic, GossipTopic) else topic
        if topic_str not in self.subscribers:
            self.subscribers[topic_str] = []
        self.subscribers[topic_str].append(handler)

    def publish(
        self, topic: GossipTopic, payload: Dict[str, Any], repo: str = "global", ttl: int = 10
    ) -> GossipMessage:
        """Broadcasts an epidemic gossip event across the mesh with adaptive scatter shaping."""
        current_scatter = self.scatter_governor.update()

        topic_str = topic.value if isinstance(topic, GossipTopic) else topic
        msg = GossipMessage(
            topic=topic_str,
            origin_node=self.node_id,
            payload={**payload, "_adaptive_scatter": current_scatter},
            repo=repo,
            ttl=ttl,
        )

        if self.pow_difficulty > 0:
            nonce, _ = mine_pow(msg.message_id, self.pow_difficulty, self.pow_nonce)
            msg.payload["pow_nonce"] = nonce

        self.seen_messages.add(msg.message_id)
        self.recent_messages.append(msg)

        file_path = self.mesh_dir / f"{msg.message_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(msg.to_dict(), f)
        except Exception as e:
            print(f"Error writing gossip message to ledger: {e}")

        self._dispatch_to_subscribers(msg)
        return msg

    def sync(self) -> List[GossipMessage]:
        new_messages: List[GossipMessage] = []
        if not self.mesh_dir.exists():
            return new_messages
        for file_path in self.mesh_dir.glob("*.json"):
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
                print(f"Error in subscriber handler: {e}")
