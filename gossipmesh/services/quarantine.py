import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name અમારી)


class ArtifactQuarantineManager:
    """Manages quarantined artifacts for security compliance and inspection."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.storage_dir = storage_dir or ".quarantine"
        self._quarantined: Dict[str, Dict[str, Any]] = {}

    def quarantine_artifact(self, artifact_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._quarantined[artifact_id] = {
            "reason": reason,
            "status": "quarantined",
            "metadata": metadata or {}
        }
        logger.warning(f"Artifact {artifact_id} quarantined: {reason}")

    def release_artifact(self, artifact_id: str) -> bool:
        if artifact_id in self._quarantined:
            del self._quarantined[artifact_id]
            return True
        return False

    def is_quarantined(self, artifact_id: str) -> bool:
        return artifact_id in self._quarantined

    def get_quarantined_artifacts(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._quarantined)
