from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ArtifactQuarantineManager:
    """Manages quarantining and releasing build/analysis artifacts."""

    def __init__(self) -> None:
        self._quarantined: Dict[str, Dict[str, Any]] = {}

    def quarantine(self, artifact_id: str, reason: str) -> None:
        self._quarantined[artifact_id] = {"reason": reason, "status": "quarantined"}
        logger.info(f"Artifact {artifact_id} quarantined: {reason}")

    def release(self, artifact_id: str) -> bool:
        if artifact_id in self._quarantined:
            del self._quarantined[artifact_id]
            logger.info(f"Artifact {artifact_id} released from quarantine.")
            return True
        return False

    def is_quarantined(self, artifact_id: str) -> bool:
        return artifact_id in self._quarantined
