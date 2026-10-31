import asyncio
import logging
import json
from typing import Dict, Any, Optional, Set
from gossipmesh.p2p.liveness import PeerManager

logger = logging.getLogger(__name__)


class GossipMessage:
    def __init__(self, msg_type: str, payload: Dict[str, Any], sender_id: str):
        self.msg_type = msg_type
        self.payload = payload
        self.sender_id = sender_id

    def serialize(self) -> str:
        return json.dumps({"msg_type": self.msg_type, "payload": self.payload, "sender_id": self.sender_id})

    @classmethod
    def deserialize(cls, data: str) -> "GossipMessage":
        obj = json.loads(data)
        return cls(obj.get("msg_type", "unknown"), obj.get("payload", {}), obj.get("sender_id", ""))


class GossipTopic:
    def __init__(self, name: str):
        self.name = name
        self.subscribers: Set[str] = set()

    def subscribe(self, node_id: str):
        self.subscribers.add(node_id)

    def unsubscribe(self, node_id: str):
        self.subscribers.discard(node_id)


class GossipNode:
    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 8000):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peer_manager = PeerManager(node_id)
        self.topics: Dict[str, GossipTopic] = {}
        self.running = False

    async def start(self):
        self.running = True
        logger.info(f"GossipNode {self.node_id} started on {self.host}:{self.port}")

    async def stop(self):
        self.running = False
        logger.info(f"GossipNode {self.node_id} stopped.")

    def register_topic(self, name: str) -> GossipTopic:
        if name not in self.topics:
            self.topics[name] = GossipTopic(name)
        return self.topics[name]

    async def broadcast(self, topic_name: str, message: GossipMessage):
        if topic_name in self.topics:
            logger.info(f"Broadcasting to topic {topic_name}: {message.msg_type}")
