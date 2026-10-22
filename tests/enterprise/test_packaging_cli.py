"""
Unit Tests for Enterprise Packaging CLI Entry Point
"""

import sys
import subprocess
import json
from pathlib import Path
import pytest
from scripts.issue_license import issue_license


@pytest.fixture
def test_license_file(tmp_path):
    """Generate a test license token file."""
    token = issue_license(
        customer_id="cli-test-corp",
        bundle_ids=["b04"],
        plan="1_year",
        private_key_path="enterprise/test_private_key.pem",
    )
    lic_file = tmp_path / "license.jwt"
    lic_file.write_text(token, encoding="utf-8")
    return lic_file


def test_packaging_cli_missing_license():
    """CLI should exit with non-zero code when no license is supplied."""
    cmd = [
        sys.executable,
        "-m",
        "enterprise.packaging",
        "--public-key-path",
        "enterprise/test_public_key.pem",
        "--license-path",
        "nonexistent.jwt",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "LICENSE ERROR" in res.stderr or "Missing license token" in res.stderr


def test_packaging_cli_json_output(test_license_file, tmp_path):
    """CLI should generate valid JSON output report when requested."""
    cmd = [
        sys.executable,
        "-m",
        "enterprise.packaging",
        "--public-key-path",
        "enterprise/test_public_key.pem",
        "--license-path",
        str(test_license_file),
        "--repo-path",
        str(tmp_path),
        "--output-format",
        "json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["license"]["customer"] == "cli-test-corp"
    assert data["license"]["offline_air_gapped"] is True
    assert data["bundle"] == "b04"
    assert "review" in data
