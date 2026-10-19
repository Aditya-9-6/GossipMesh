import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GossipProtocolHandler:
    """Handles serialization, deserialization, and routing of gossip messages."""

    def __init__(self, node_id: str) -> None:
        self._node_id = node_id

    def pack_message(self, msg_type: str, payload: Dict[str, Any]) -> bytes:
        """Packs a gossip message into wire format."""
        import json

        envelope = {
            "node_id": self._node_id,
            "type": msg_type,
            "payload": payload,
        }
        return json.dumps(envelope).encode("utf-8")

    def unpack_message(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        """Unpacks and validates a gossip message from wire format."""
        import json

        try:
            return json.loads(raw_data.decode("utf-8"))
        except Exception as e:
            logger.error("Failed to unpack gossip message: %s", e)
            return None


# Provide alias for backward compatibility
GossipProtocol = GossipProtocolHandler
