"""
Unit Tests for Infrastructure-Aware Security & Architecture Reviewer
"""

import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import pytest
except ImportError:
    pytest = None

from scripts.infrastructure_reviewer import review, scan_file, InfrastructureFinding


def test_clean_repo_high_score(tmp_path):
    """A clean repository with no infrastructure violations should score 100 (Grade A)."""
    # Create clean dockerfile
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12-slim\nRUN useradd -u 1000 reviewer\nUSER reviewer\nWORKDIR /app\n")

    result = review(repo_root=tmp_path)
    assert result["score"] == 100
    assert result["grade"] == "A"
    assert result["total_findings"] == 0


def test_detect_hardcoded_secrets(tmp_path):
    """Verify detection of hardcoded API keys and secrets."""
    tf_file = tmp_path / "main.tf"
    tf_file.write_text('provider "aws" {\n  region = "us-east-1"\n  access_key = "AKIA12345678EXAMPLEKEY"\n}\n')

    result = review(repo_root=tmp_path)
    assert result["total_findings"] >= 1
    rule_ids = [f["rule_id"] for f in result["findings"]]
    assert "INFRA-SEC-001" in rule_ids
    assert result["score"] < 100


def test_detect_docker_root_and_latest(tmp_path):
    """Verify detection of Docker root user and unpinned latest base image."""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text('FROM ubuntu:latest\nRUN apt-get update\nCMD ["bash"]\n')

    result = review(repo_root=tmp_path)
    rule_ids = [f["rule_id"] for f in result["findings"]]
    assert "INFRA-DOCKER-001" in rule_ids  # latest tag
    assert "INFRA-DOCKER-002" in rule_ids  # missing user


def test_detect_kubernetes_privileged(tmp_path):
    """Verify detection of Kubernetes privileged containers."""
    k8s_dir = tmp_path / "k8s"
    k8s_dir.mkdir()
    pod_yaml = k8s_dir / "deployment.yaml"
    pod_yaml.write_text(
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "spec:\n"
        "  template:\n"
        "    spec:\n"
        "      containers:\n"
        "      - name: app\n"
        "        securityContext:\n"
        "          privileged: true\n"
    )

    result = review(repo_root=tmp_path)
    rule_ids = [f["rule_id"] for f in result["findings"]]
    assert "INFRA-K8S-001" in rule_ids


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        test_clean_repo_high_score(p)
    print("[OK] test_clean_repo_high_score passed.")

    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        test_detect_hardcoded_secrets(p)
    print("[OK] test_detect_hardcoded_secrets passed.")

    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        test_detect_docker_root_and_latest(p)
    print("[OK] test_detect_docker_root_and_latest passed.")

    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        test_detect_kubernetes_privileged(p)
    print("[OK] test_detect_kubernetes_privileged passed.")

    print("\n[SUCCESS] ALL INFRASTRUCTURE REVIEWER TESTS PASSED 100%!")
