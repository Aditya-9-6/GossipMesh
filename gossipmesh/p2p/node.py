import os
import json
import time
import uuid
import asyncio
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
from gossipmesh.p2p.dht import KademliaDHT, DHTNode, K

class GossipTopic(str, Enum):
    ARTEFACT_BROADCAST = "artefact_broadcast"
    AGENT_HEARTBEAT = "agent_heartbeat"
    CONSENSUS_VOTE = "consensus_vote"
    SECURITY_ALERT = "security_alert"


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
            topic=data["topic"],
            origin_node=data["origin_node"],
            payload=data["payload"],
            repo=data.get("repo", "global"),
            message_id=data.get("message_id"),
            vector_clock=data.get("vector_clock", {}),
            timestamp=data.get("timestamp"),
            ttl=data.get("ttl", 10),
        )


class GossipNode:
    """Decentralized Gossip Peer Node with Kademlia DHT support.
Communicates via a shared ledger directory (file-backed mesh) or local bus."""

    def __init__(self, node_id: str, mesh_dir: str | None = None, host: str = "127.0.0.1", port: int = 8000):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path(".gossip_mesh/ledger")
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.seen_messages: set = set()
        self.subscribers: Dict[str, List[Callable[[GossipMessage], None]]] = {}
        self.recent_messages: deque = deque(maxlen=100)
        
        # Initialize Kademlia DHT
        dht_local_node = DHTNode(node_id=self.node_id, host=self.host, port=self.port)
        self.dht = KademliaDHT(dht_local_node)
        
        self._load_seen_history()

    def _load_seen_history(self):
        """Loads message IDs previously witnessed to prevent duplicate processing."""
        for path in self.mesh_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "message_id" in data:
                        self.seen_messages.add(data["message_id"])
            except Exception:
                continue

    def subscribe(self, topic: GossipTopic, handler: Callable[[GossipMessage], None]):
        """Registers a reactive listener callback for a gossip topic."""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(handler)

    def publish(self, topic: GossipTopic, payload: Dict[str, Any], repo: str = "global", ttl: int = 10) -> GossipMessage:
        """Broadcasts an epidemic gossip event across the mesh."""
        msg = GossipMessage(
            topic=topic,
            origin_node=self.node_id,
            payload=payload,
            repo=repo,
            ttl=ttl
        )
        self.seen_messages.add(msg.message_id)
        self.recent_messages.append(msg)
        
        # Persist to ledger file
        msg_path = self.mesh_dir / f"{msg.message_id}.json"
        with open(msg_path, "w", encoding="utf-8") as f:
            json.dump(msg.to_dict(), f, indent=2)

        self._dispatch_local(msg)
        return msg

    def _dispatch_local(self, msg: GossipMessage):
        handlers = self.subscribers.get(msg.topic, [])
        for handler in handlers:
            try:
                handler(msg)
            except Exception:
                pass

    def sync(self) -> List[GossipMessage]:
        """Runs anti-entropy synchronization: scans the shared ledger for newly
arrived gossip messages from other peer nodes."""
        new_messages = []
        for path in self.mesh_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    msg = GossipMessage.from_dict(data)
                    if msg.message_id not in self.seen_messages:
                        self.seen_messages.add(msg.message_id)
                        self.recent_messages.append(msg)
                        new_messages.append(msg)
                        self._dispatch_local(msg)
            except Exception:
                continue
        return new_messages

    def heartbeat(self):
        """Updates this node's live liveness timestamp."""
        pass

    def get_recent_messages(self, topic: Optional[GossipTopic] = None, limit: int = 50) -> List[GossipMessage]:
        """Fetches the latest gossip messages from the in-memory cache."""
        msgs = list(self.recent_messages)
        if topic:
            msgs = [m for m in msgs if m.topic == topic]
        return msgs[-limit:]

    def cleanup_ledger(self):
        """Removes expired messages from the ledger based on TTL."""
        now = time.time()
        for path in self.mesh_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    timestamp = data.get("timestamp", now)
                    ttl = data.get(
                        "ttl", 10
                    )
                    if (now - timestamp) > (ttl * 60):
                        path.unlink()
            except Exception:
                continue

    async def discover_peer(self, node_id: str, host: str, port: int):
        """Discovers a peer and adds it to the local Kademlia DHT."""
        node = DHTNode(node_id=node_id, host=host, port=port)
        await self.dht.add_node(node)

    async def find_closest_peers(self, target_id: str) -> List[DHTNode]:
        """Finds the closest peers to a target ID using XOR distance metric."""
        return await self.dht.find_close_nodes(target_id)
