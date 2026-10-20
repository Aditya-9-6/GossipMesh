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
        daily_limit: int = 10,
        require_human_approval: bool = True,
        allow_force_push: bool = False,
        allow_auto_merge: bool = False,
    ):
        self.allowed_repositories: Set[str] = set(allowed_repositories or [])
        self.allowed_labels: Set[str] = set(allowed_labels or [])
        self.daily_limit: int = daily_limit
        self.require_human_approval: bool = require_human_approval

        # Unsafe defaults should be disabled
        self.allow_force_push: bool = allow_force_push
        self.allow_auto_merge: bool = allow_auto_merge

        self.is_active: bool = True

        self._metrics: Dict[str, int] = {
            "runs_attempted": 0,
            "runs_allowed": 0,
            "runs_rejected_repo": 0,
            "runs_rejected_label": 0,
            "runs_rejected_limit": 0,
            "runs_rejected_shutdown": 0,
        }
        self._runs_today: int = 0

    def is_automation_allowed(self, repo: str, labels: List[str] = None) -> bool:
        """Checks if automation is allowed for a given repository and label combination."""
        self._metrics["runs_attempted"] += 1

        if not self.is_active:
            self._metrics["runs_rejected_shutdown"] += 1
            return False

        if self.allowed_repositories and repo not in self.allowed_repositories:
            self._metrics["runs_rejected_repo"] += 1
            return False

        if self.allowed_labels:
            if not labels or not any(label in self.allowed_labels for label in labels):
                self._metrics["runs_rejected_label"] += 1
                return False

        if self._runs_today >= self.daily_limit:
            self._metrics["runs_rejected_limit"] += 1
            return False

        self._metrics["runs_allowed"] += 1
        return True

    def record_run(self) -> bool:
        """Records a successful automation run towards the daily limit."""
        if self._runs_today < self.daily_limit:
            self._runs_today += 1
            return True
        return False

    def reset_daily_limit(self) -> None:
        """Resets the daily limit counter (typically called by a scheduler)."""
        self._runs_today = 0

    def get_metrics(self) -> Dict[str, int]:
        """Returns the collected metrics for canary mode operations."""
        return self._metrics.copy()

    def shutdown(self) -> None:
        """Immediately disables automation capabilities."""
        self.is_active = False
