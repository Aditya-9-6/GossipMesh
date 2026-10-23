"""Safety flags, kill switch, and safe defaults for GossipMesh automation (Tasks 8 & 18).
Enforces environment-controlled safety switches:
- GOSSIPMESH_AUTOMATION_ENABLED: Master kill-switch
- GOSSIPMESH_ALLOW_PR_CREATION: Guard for opening Pull Requests
- GOSSIPMESH_ALLOW_PUSH: Guard for git push
- GOSSIPMESH_ALLOW_FORCE_PUSH: Guard for git push --force
- GOSSIPMESH_ALLOW_AUTO_MERGE: Guard for automated squash/merge
- GOSSIPMESH_MAX_FILES_PER_CHANGE: Limit on number of files mutated
- GOSSIPMESH_MAX_DAILY_RUNS: Daily execution run ceiling
- GOSSIPMESH_MAX_DAILY_PR_CREATION: Daily PR creation ceiling
"""

import os
import sys
from typing import Tuple


def _bool_env(var_name: str, default: bool = False) -> bool:
    val = os.getenv(var_name)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on", "enable", "enabled")


def _int_env(var_name: str, default: int) -> int:
    val = os.getenv(var_name)
    if not val:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


class SafetyConfig:
    """Enterprise safety configuration with secure-by-default switches."""

    @property
    def AUTOMATION_ENABLED(self) -> bool:
        """Master kill-switch. If False, all automation immediately halts."""
        return _bool_env("GOSSIPMESH_AUTOMATION_ENABLED", default=True)

    @property
    def ALLOW_PR_CREATION(self) -> bool:
        """Guard for opening Pull Requests. Defaults to False (Task 18)."""
        return _bool_env("GOSSIPMESH_ALLOW_PR_CREATION", default=False)

    @property
    def ALLOW_PUSH(self) -> bool:
        """Guard for git push. Defaults to False (Task 18)."""
        return _bool_env("GOSSIPMESH_ALLOW_PUSH", default=False)

    @property
    def ALLOW_FORCE_PUSH(self) -> bool:
        """Guard for git push --force. Defaults to False (Task 18)."""
        return _bool_env("GOSSIPMESH_ALLOW_FORCE_PUSH", default=False)

    @property
    def ALLOW_AUTO_MERGE(self) -> bool:
        """Guard for auto-merging PRs. Defaults to False (Task 18)."""
        return _bool_env("GOSSIPMESH_ALLOW_AUTO_MERGE", default=False)

    @property
    def MAX_FILES_PER_CHANGE(self) -> int:
        """Maximum number of files allowed in a single AI patch."""
        return _int_env("GOSSIPMESH_MAX_FILES_PER_CHANGE", default=25)

    @property
    def MAX_DAILY_RUNS(self) -> int:
        """Daily ceiling for total automated runs."""
        return _int_env("GOSSIPMESH_MAX_DAILY_RUNS", default=100)

    @property
    def MAX_DAILY_PR_CREATION(self) -> int:
        """Daily ceiling for total automated PR creations."""
        return _int_env("GOSSIPMESH_MAX_DAILY_PR_CREATION", default=20)


safety = SafetyConfig()


def check_automation_kill_switch() -> Tuple[bool, str]:
    """Checks if the master automation kill switch is triggered."""
    if not safety.AUTOMATION_ENABLED:
        return False, "Automation aborted: GOSSIPMESH_AUTOMATION_ENABLED is False (Kill-switch active)."
    return True, ""


def check_pr_creation_allowed() -> Tuple[bool, str]:
    """Checks if PR creation is authorized by safety configuration."""
    if not safety.ALLOW_PR_CREATION:
        return False, "PR creation blocked: GOSSIPMESH_ALLOW_PR_CREATION is disabled by default."
    return True, ""


def check_push_allowed(force: bool = False) -> Tuple[bool, str]:
    """Checks if pushing changes to remote is authorized."""
    if not safety.ALLOW_PUSH:
        return False, "Git push blocked: GOSSIPMESH_ALLOW_PUSH is disabled by default."
    if force and not safety.ALLOW_FORCE_PUSH:
        return False, "Git force push blocked: GOSSIPMESH_ALLOW_FORCE_PUSH is disabled by default."
    return True, ""


def check_auto_merge_allowed() -> Tuple[bool, str]:
    """Checks if auto-merging PRs into main is authorized."""
    if not safety.ALLOW_AUTO_MERGE:
        return False, "Auto-merge blocked: GOSSIPMESH_ALLOW_AUTO_MERGE is disabled by default."
    return True, ""


def check_file_mutation_limit(num_files: int) -> Tuple[bool, str]:
    """Validates that modified file count is within safe limits."""
    if num_files > safety.MAX_FILES_PER_CHANGE:
        return (
            False,
            f"File mutation limit exceeded: {num_files} files changed (max allowed: {safety.MAX_FILES_PER_CHANGE}).",
        )
    return True, ""
