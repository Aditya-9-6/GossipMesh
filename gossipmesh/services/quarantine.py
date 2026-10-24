import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArtifactQuarantineManager:
    """Manages quarantined artifacts for security compliance."""

    def __init__(self) -> None:
        self._quarantined: Dict[str, Dict[str, Any]] = {}

    def quarantine_artifact(self, artifact_id: str, reason: str) -> None:
        self._quarantined[artifact_id] = {"reason": reason, "status": "quarantined"}
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
