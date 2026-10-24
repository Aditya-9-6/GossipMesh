from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ArtifactQuarantineManager:
    """Manages quarantined artifacts for security inspection and sandboxing."""

    def __init__(self) -> None:
        self._quarantined: Dict[str, Dict[str, Any]] = {}

    def quarantine_artifact(self, artifact_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._quarantined[artifact_id] = {"reason": reason, "metadata": metadata or {}}
        logger.warning(f"Artifact {artifact_id} quarantined: {reason}")

    def is_quarantined(self, artifact_id: str) -> bool:
        return artifact_id in self._quarantined

    def release_artifact(self, artifact_id: str) -> None:
        self._quarantined.pop(artifact_id, None)
        logger.info(f"Artifact {artifact_id} released from quarantine.")

    def list_quarantined(self) -> List[str]:
        return list(self._quarantined.keys())
