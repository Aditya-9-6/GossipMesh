"""
Unit Tests for Infrastructure-Aware Security & Architecture Reviewer
"""

import pytest
from pathlib import Path
from scripts.infrastructure_reviewer import review, scan_file, InfrastructureFinding


def test_clean_repo_high_score(tmp_path):
    """A clean repository with no infrastructure violations should score 100 (Grade A)."""
    # Create clean dockerfile
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM python:3.12-slim\n"
        "RUN useradd -u 1000 reviewer\n"
        "USER reviewer\n"
        "WORKDIR /app\n"
    )

    result = review(repo_root=tmp_path)
    assert result["score"] == 100
    assert result["grade"] == "A"
    assert result["total_findings"] == 0


def test_detect_hardcoded_secrets(tmp_path):
    """Verify detection of hardcoded API keys and secrets."""
    tf_file = tmp_path / "main.tf"
    tf_file.write_text(
        'provider "aws" {\n'
        '  region = "us-east-1"\n'
        '  access_key = "AKIA12345678EXAMPLEKEY"\n'
        '}\n'
    )

    result = review(repo_root=tmp_path)
    assert result["total_findings"] >= 1
    rule_ids = [f["rule_id"] for f in result["findings"]]
    assert "INFRA-SEC-001" in rule_ids
    assert result["score"] < 100


def test_detect_docker_root_and_latest(tmp_path):
    """Verify detection of Docker root user and unpinned latest base image."""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM ubuntu:latest\n"
        "RUN apt-get update\n"
        "CMD [\"bash\"]\n"
    )

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
