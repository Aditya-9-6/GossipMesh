import os
import pytest
from gossipmesh.core.safety import (
    SafetyConfig,
    check_automation_kill_switch,
    check_pr_creation_allowed,
    check_push_allowed,
    check_auto_merge_allowed,
    check_file_mutation_limit,
)


def test_safety_defaults_are_disabled_by_default():
    """Proves Task 18: Unsafe operations are disabled by default."""
    # Ensure env vars are not set
    env_vars = [
        "GOSSIPMESH_ALLOW_PR_CREATION",
        "GOSSIPMESH_ALLOW_PUSH",
        "GOSSIPMESH_ALLOW_FORCE_PUSH",
        "GOSSIPMESH_ALLOW_AUTO_MERGE",
    ]
    for v in env_vars:
        os.environ.pop(v, None)

    cfg = SafetyConfig()
    assert cfg.ALLOW_PR_CREATION is False
    assert cfg.ALLOW_PUSH is False
    assert cfg.ALLOW_FORCE_PUSH is False
    assert cfg.ALLOW_AUTO_MERGE is False
    assert cfg.AUTOMATION_ENABLED is True


def test_safety_kill_switch():
    """Proves Task 8: GOSSIPMESH_AUTOMATION_ENABLED acts as master kill switch."""
    os.environ["GOSSIPMESH_AUTOMATION_ENABLED"] = "false"
    try:
        allowed, reason = check_automation_kill_switch()
        assert allowed is False
        assert "Kill-switch active" in reason
    finally:
        os.environ["GOSSIPMESH_AUTOMATION_ENABLED"] = "true"


def test_safety_checks_respect_explicit_flags():
    """Proves Task 8: Flags enable operations when explicitly opted in."""
    os.environ["GOSSIPMESH_ALLOW_PR_CREATION"] = "1"
    os.environ["GOSSIPMESH_ALLOW_PUSH"] = "true"
    os.environ["GOSSIPMESH_ALLOW_AUTO_MERGE"] = "yes"
    try:
        pr_ok, _ = check_pr_creation_allowed()
        assert pr_ok is True

        push_ok, _ = check_push_allowed(force=False)
        assert push_ok is True

        merge_ok, _ = check_auto_merge_allowed()
        assert merge_ok is True
    finally:
        os.environ.pop("GOSSIPMESH_ALLOW_PR_CREATION", None)
        os.environ.pop("GOSSIPMESH_ALLOW_PUSH", None)
        os.environ.pop("GOSSIPMESH_ALLOW_AUTO_MERGE", None)


def test_safety_file_mutation_limit():
    """Proves Task 8: File mutation limit rejects excessive files."""
    os.environ["GOSSIPMESH_MAX_FILES_PER_CHANGE"] = "10"
    try:
        ok, _ = check_file_mutation_limit(5)
        assert ok is True

        fail, msg = check_file_mutation_limit(15)
        assert fail is False
        assert "File mutation limit exceeded" in msg
    finally:
        os.environ.pop("GOSSIPMESH_MAX_FILES_PER_CHANGE", None)
