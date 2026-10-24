"""
Production Secret & Credential Scanning Engine (Task 106).

Detects accidental leaks of API keys, private keys, database credentials,
and personal access tokens across source files, test fixtures, configurations,
and review artifacts.
"""

from __future__ import annotations

import re
import subprocess
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SecretFinding:
    rule_id: str
    description: str
    file_path: str
    line_number: int
    matched_text_masked: str
    severity: str = "HIGH"


# Regular expression rules for high-confidence secret detection
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "severity": "CRITICAL",
        "description": "AWS Access Key ID",
    },
    "GM-SEC-AWS-SECRET": {
        "pattern": re.compile(r"(?:^|[^A-Za-z0-9/+=])([A-Za-z0-9/+=]{40})(?:[^A-Za-z0-9/+=]|$)"),
        "severity": "CRITICAL",
        "description": "Potential AWS Secret Access Key detected",
    },
    "GM-SEC-GITHUB-PAT": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{36,})"),
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token",
    },
    "GM-SEC-GITHUB-TOKEN": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36})"),
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token detected",
    },
    "GM-SEC-OPENAI-KEY": {
        "pattern": re.compile(r"(sk-(?:live-)?[a-zA-Z0-9_-]{32,})"),
        "severity": "HIGH",
        "description": "OpenAI / LLM API Key",
    },
    "GM-SEC-STRIPE-LIVE": {
        "pattern": re.compile(r"(sk_live_[a-zA-Z0-9]{24,})"),
        "severity": "HIGH",
        "description": "Stripe Live Secret Key",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})"),
        "severity": "CRITICAL",
        "description": "Slack Token / Credential",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        "severity": "CRITICAL",
        "description": "Private cryptographic key detected",
    },
    "GM-SEC-JWT": {
        "pattern": re.compile(r"eyJ[a-zA-Z0-9-_]+\.eyJ[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]+"),
        "severity": "HIGH",
        "description": "JSON Web Token (JWT) detected",
    },
    "GM-SEC-GENERIC-SECRET": {
        "pattern": re.compile(
            r"(?i)(?:secret|api_key|password|passwd|auth_token)\s*[:=]\s*['\"]([a-zA-Z0-9-_]{8,64})['\"]"
        ),
        "severity": "HIGH",
        "description": "Hardcoded secret assignment detected",
    },
}

# Whitelist safe placeholder / test tokens
WHITELIST_PLACEHOLDERS = {
    "sk_test_dummy",
    "sk_test_mock",
    "whsec_dummy",
    "fake_key",
    "placeholder",
    "dummy_secret",
}


def mask_secret(secret_str: str) -> str:
    """Masks secret keeping only the first 4 and last 2 characters."""
    if len(secret_str) <= 8:
        return "****"
    return f"{secret_str[:4]}...{secret_str[-2:]}"


class SecretScanner:
    def scan_diff(self, diff_text: str) -> list:
        # Placeholder implementation for secret scanner diff analysis
        return []


class SecretScannerEngine:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def is_whitelisted(self, text: str) -> bool:
        """Determines if a matched pattern is an intentional test mock or placeholder."""
        text_lower = text.lower()
        return any(placeholder in text_lower for placeholder in WHITELIST_PLACEHOLDERS)

    def scan_content(self, content: str, file_path: str = "inline") -> List[SecretFinding]:
        """Scans a text payload line-by-line for secret patterns."""
        findings: List[SecretFinding] = []
        lines = content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            for rule_id, rule_info in self.rules.items():
                pattern: re.Pattern = rule_info["pattern"]
                match = pattern.search(line)
                if match:
                    matched_val = match.group(1) if match.groups() else match.group(0)
                    if not self.is_whitelisted(matched_val):
                        findings.append(
                            SecretFinding(
                                rule_id=rule_id,
                                description=rule_info["description"],
                                file_path=file_path,
                                line_number=line_num,
                                matched_text_masked=mask_secret(matched_val),
                                severity=rule_info.get("severity", "HIGH"),
                            )
                        )
        return findings

    def scan_text(self, text: str, source_identifier: str = "inline") -> List[Dict[str, Any]]:
        findings = []
        lines = text.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for rule_id, rule_def in self.rules.items():
                pattern = rule_def["pattern"]
                for match in pattern.finditer(line):
                    matched_val = match.group(1) if match.groups() else match.group(0)
                    if not self.is_whitelisted(matched_val):
                        findings.append(
                            {
                                "rule_id": rule_id,
                                "severity": rule_def.get("severity", "HIGH"),
                                "description": rule_def["description"],
                                "source": source_identifier,
                                "line": line_idx,
                                "snippet": line.strip()[:100],
                                "matched_text_masked": mask_secret(matched_val),
                            }
                        )
        return findings

    def scan_file(self, path: Path | str) -> List[SecretFinding]:
        """Scans an individual file on disk."""
        p = Path(path).resolve()
        if not p.is_file():
            return []
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, file_path=str(p))
        except Exception as e:
            logger.error(f"Failed to scan file {p}: {e}")
            return []

    def scan_git_diff(self, repo_path: Path) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return self.scan_text(result.stdout, source_identifier="git-diff")
        except Exception as e:
            logger.error(f"Failed to run git diff on {repo_path}: {e}")
            return []
