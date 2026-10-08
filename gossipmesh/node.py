"""
P2P Epidemic Gossip Protocol Node.
Implements vector clocks, anti-entropy synchronization, and decentralized message dissemination.
"""

import os
import json
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

class GossipTopic(str, Enum):
    ANTI_PATTERNS = "anti_patterns"
    BEST_PRACTICES = "best_practices"
    CROSS_REPO_SPECS = "cross_repo_specs"
    RED_TEAM_VULNS = "red_team_vulns"
    CONSENSUS_VOTES = "consensus_votes"
    PERF_TELEMETRY = "perf_telemetry"
    TASK_AUCTIONS = "task_auctions"
    HEARTBEATS = "heartbeats"

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
        self.message_id = message_id or str(uuid.uuid4())
        self.topic = topic
        self.origin_node = origin_node
        self.repo = repo
        self.payload = payload
        self.vector_clock = vector_clock or {}
        self.timestamp = timestamp or time.time()
        self.ttl = ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "topic": self.topic,
            "origin_node": self.origin_node,
            "repo": self.repo,
            "payload": self.payload,
            "vector_clock": self.vector_clock,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GossipMessage":
        return cls(
            topic=data.get("topic", "general"),
            origin_node=data.get("origin_node", "unknown"),
            payload=data.get("payload", {}),
            repo=data.get("repo", "global"),
            message_id=data.get("message_id"),
            vector_clock=data.get("vector_clock", {}),
            timestamp=data.get("timestamp"),
            ttl=data.get("ttl", 10),
        )

class GossipNode:
    """
    Decentralized Gossip Peer Node.
    Communicates via a shared ledger directory (file-backed mesh) or local bus.
    """
    def __init__(self, node_id: str, mesh_dir: Optional[str] = None):
        self.node_id = node_id
        if mesh_dir:
            self.mesh_dir = Path(mesh_dir).resolve()
        else:
            # Fallback to shared Google Drive or User home
            drive_mesh = Path("G:/My Drive/.gossip_mesh")
            if drive_mesh.parent.exists():
                self.mesh_dir = drive_mesh
            else:
                self.mesh_dir = Path.home() / ".gossip_mesh"

        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.mesh_dir / "ledger.jsonl"
        self.heartbeats_file = self.mesh_dir / "heartbeats.json"

        self.clock_seq = 0
        self.seen_messages: set = set()
        self.subscriptions: Dict[str, List[Callable[[GossipMessage], None]]] = {}

        # Initial anti-entropy catchup
        self._load_seen_history()
        self.heartbeat()

    def _load_seen_history(self):
        """Loads message IDs previously witnessed to prevent duplicate processing."""
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                mid = data.get("message_id")
                                if mid:
                                    self.seen_messages.add(mid)
                            except Exception:
                                pass
            except Exception:
                pass

    def subscribe(self, topic: GossipTopic, handler: Callable[[GossipMessage], None]):
        """Registers a reactive listener callback for a gossip topic."""
        t_val = topic.value if isinstance(topic, GossipTopic) else str(topic)
        if t_val not in self.subscriptions:
            self.subscriptions[t_val] = []
        self.subscriptions[t_val].append(handler)

    def publish(self, topic: GossipTopic, payload: Dict[str, Any], repo: str = "global", ttl: int = 10) -> GossipMessage:
        """Broadcasts an epidemic gossip event across the mesh."""
        t_val = topic.value if isinstance(topic, GossipTopic) else str(topic)
        self.clock_seq += 1
        msg = GossipMessage(
            topic=t_val,
            origin_node=self.node_id,
            payload=payload,
            repo=repo,
            vector_clock={self.node_id: self.clock_seq},
            ttl=ttl,
        )

        self.seen_messages.add(msg.message_id)

        # Atomic append to ledger
        line = json.dumps(msg.to_dict()) + "\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)

        # Self-dispatch to local listeners
        if t_val in self.subscriptions:
            for handler in self.subscriptions[t_val]:
                try:
                    handler(msg)
                except Exception as e:
                    print(f"[{self.node_id}] Gossip handler error: {e}")

        return msg

    def sync(self) -> List[GossipMessage]:
        """
        Runs anti-entropy synchronization: scans the shared ledger for newly
        arrived gossip messages from other peer nodes.
        """
        new_messages = []
        if not self.log_file.exists():
            return new_messages

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        mid = data.get("message_id")
                        if mid and mid not in self.seen_messages:
                            self.seen_messages.add(mid)
                            msg = GossipMessage.from_dict(data)
                            new_messages.append(msg)
                            # Dispatch to subscribers
                            if msg.topic in self.subscriptions:
                                for handler in self.subscriptions[msg.topic]:
                                    try:
                                        handler(msg)
                                    except Exception as e:
                                        print(f"[{self.node_id}] Gossip dispatch error: {e}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[{self.node_id}] Sync error: {e}")

        return new_messages

    def heartbeat(self):
        """Updates this node's live liveness timestamp."""
        hb = {}
        if self.heartbeats_file.exists():
            try:
                hb = json.loads(self.heartbeats_file.read_text(encoding="utf-8"))
            except Exception:
                hb = {}

        hb[self.node_id] = {
            "last_seen": time.time(),
            "clock_seq": self.clock_seq,
        }
        try:
            self.heartbeats_file.write_text(json.dumps(hb, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_recent_messages(self, topic: Optional[GossipTopic] = None, limit: int = 50) -> List[GossipMessage]:
        """Fetches the latest gossip messages from the ledger."""
        messages = []
        if not self.log_file.exists():
            return messages

        t_val = topic.value if isinstance(topic, GossipTopic) else (str(topic) if topic else None)
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if t_val is None or data.get("topic") == t_val:
                                messages.append(GossipMessage.from_dict(data))
                        except Exception:
                            pass
        except Exception:
            pass

        return messages[-limit:]
