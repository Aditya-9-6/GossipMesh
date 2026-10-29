import os
import json
import time
import uuid
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
import threading

from gossipmesh.p2p.health import SlidingWindowPeerHealthScorecard, PeerHealthConfig
from gossipmesh.p2p.dht import KademliaDHT, KademliaNodeInfo


class GossipTopic(str, Enum):
    AGENT_SPAWN = "agent:spawn"
    AGENT_EVENT = "agent:event"
    CODE_REVIEW = "code:review"
    BUILD_STATUS = "build:status"
    SECURITY_ALERT = "security:alert"
    CONSENSUS = "consensus"
    HEARTBEAT = "heartbeat"
    TASK_BID = "task_bid"
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


class PeerNode:
    def __init__(self, peer_id: str, address: str, health_config: Optional[PeerHealthConfig] = None) -> None:
        self.peer_id = peer_id
        self.address = address
        self.scorecard = SlidingWindowPeerHealthScorecard(health_config)
        self.connected_at = time.time()
        self._lock = threading.Lock()

    def record_interaction(self, latency_ms: float, dropped: bool = False, violated: bool = False) -> float:
        return self.scorecard.record_sample(latency_ms, dropped, violated)

    def is_healthy(self) -> bool:
        metrics = self.scorecard.get_metrics()
        return not metrics["is_quarantined"]

    def get_status(self) -> Dict[str, Any]:
        metrics = self.scorecard.get_metrics()
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "connected_at": self.connected_at,
            **metrics,
        }


class GossipNode:
    """Decentralized Gossip Peer Node with Kademlia DHT integration and backward compatibility."""

    def __init__(self, node_id: str, mesh_dir: Optional[str] = None, port: int = 8000):
        self.node_id = node_id
        self.port = port
        self.dht = KademliaDHT(node_id)
        if mesh_dir:
            self.mesh_dir = Path(mesh_dir).resolve()
        elif os.environ.get("GOSSIPMESH_DIR"):
            self.mesh_dir = Path(os.environ.get("GOSSIPMESH_DIR", "")).resolve()
        else:
            self.mesh_dir = Path.home() / ".gossip_mesh"

        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.mesh_dir / "ledger.jsonl"
        self.heartbeats_file = self.mesh_dir / "heartbeats.json"

        self.clock_seq = 0
        self.seen_messages: set = set()
        self.subscriptions: Dict[str, List[Callable[[GossipMessage], None]]] = {}
        self._message_cache: deque[GossipMessage] = deque(maxlen=10000)

        self._load_seen_history()
        self.heartbeat()

    def _load_seen_history(self):
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
                                    self._message_cache.append(GossipMessage.from_dict(data))
                            except Exception:
                                pass
            except Exception:
                pass

    def subscribe(self, topic: GossipTopic | str, handler: Callable[[GossipMessage], None]):
        t_val = topic.value if isinstance(topic, GossipTopic) else str(topic)
        if t_val not in self.subscriptions:
            self.subscriptions[t_val] = []
        self.subscriptions[t_val].append(handler)

    def publish(
        self, topic: GossipTopic | str, payload: Dict[str, Any], repo: str = "global", ttl: int = 10
    ) -> GossipMessage:
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
        self._message_cache.append(msg)

        line = json.dumps(msg.to_dict()) + "\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)

        if t_val in self.subscriptions:
            for handler in self.subscriptions[t_val]:
                try:
                    handler(msg)
                except Exception:
                    pass

        return msg

    def sync(self) -> List[GossipMessage]:
        new_messages: list[GossipMessage] = []
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
                            self._message_cache.append(msg)
                            if msg.topic in self.subscriptions:
                                for handler in self.subscriptions[msg.topic]:
                                    try:
                                        handler(msg)
                                    except Exception:
                                        pass
                    except Exception:
                        pass
        except Exception:
            pass

        return new_messages

    def heartbeat(self):
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

    def get_recent_messages(self, topic: Optional[GossipTopic | str] = None, limit: int = 50) -> List[GossipMessage]:
        t_val = topic.value if isinstance(topic, GossipTopic) else (str(topic) if topic else None)
        filtered = []
        for msg in reversed(self._message_cache):
            if t_val is None or msg.topic == t_val:
                filtered.append(msg)
                if len(filtered) >= limit:
                    break
        filtered.reverse()
        return filtered

    def cleanup_ledger(self):
        if not self.log_file.exists():
            return
        valid_lines = []
        now = time.time()
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        msg_time = data.get("timestamp", 0)
                        msg_ttl = data.get("ttl", 10)
                        if msg_time + (msg_ttl * 3600) >= now:
                            valid_lines.append(line_str)
                    except Exception:
                        pass

            with open(self.log_file, "w", encoding="utf-8") as f:
                for line in valid_lines:
                    f.write(line + "\n")

            self._message_cache.clear()
            for line_str in valid_lines:
                try:
                    data = json.loads(line_str)
                    self._message_cache.append(GossipMessage.from_dict(data))
                except Exception:
                    pass
        except Exception:
            pass
