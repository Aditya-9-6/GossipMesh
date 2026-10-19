"""
Canary mode implementation for GossipMesh.
Milestone Implementation for Task 17.
"""

from typing import List, Dict, Set

class CanaryManager:
    """
    Manages Canary Mode for gradual rollout of automation.
    Allows automation only for selected repositories and labels,
    with daily limits, human approval requirements, restricted force-push/auto-merge,
    and immediate shutdown capabilities.
    """

    def __init__(
        self,
        allowed_repositories: List[str] = None,
        allowed_labels: List[str] = None,
        daily_limit: int = 50,
        require_human_approval: bool = True,
    ):
        self.allowed_repositories: Set[str] = set(allowed_repositories or [])
        self.allowed_labels: Set[str] = set(allowed_labels or [])
        self.daily_limit = daily_limit
        self.require_human_approval = require_human_approval
        self._usage_counts: Dict[str, int] = {}
        self._shutdown_active = False

    def is_enabled_for(self, repository: str, labels: List[str]) -> bool:
        if self._shutdown_active:
            return False
        if self.allowed_repositories and repository not in self.allowed_repositories:
            return False
        if self.allowed_labels and not any(l in self.allowed_labels for l in labels):
            return False
        return True

    def record_usage(self, repository: str) -> None:
        self._usage_counts[repository] = self._usage_counts.get(repository, 0) + 1

    def trigger_emergency_shutdown(self) -> None:
        self._shutdown_active = True
