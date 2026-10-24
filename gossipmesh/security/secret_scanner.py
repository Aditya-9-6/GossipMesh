"""
Production Secret & Credential Scanning Engine (Task 106).

Detects accidental leaks of API keys, private keys, database credentials,
and personal access tokens across source files, test fixtures, configurations,
and review artifacts.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class SecretFinding:
    rule_id: str
    description: str
    file_path: str
    line_number: int
    matched_text_masked: str


# Regular expression rules for high-confidence secret detection (combined from both branches)
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "severity": "HIGH",
        "description": "AWS Access Key ID detected",
    },
    "GM-SEC-AWS-SECRET": {
        "pattern": re.compile(r"(?:^|[^A-Za-z0-9/+=])([0-9a-zA-Z/+]{40})(?:[^A-Za-z0-9/+=]|$)"),
        "severity": "CRITICAL",
        "description": "Potential AWS Secret Access Key detected (context-dependent)",
    },
    "GM-SEC-GITHUB-TOKEN": {
        "pattern": re.compile(r"(gh[pous]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{36,})"),
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token detected",
    },
    "GM-SEC-OPENAI-KEY": {
        "pattern": re.compile(r"(sk-(?:live-)?[a-zA-Z0-9_-]{32,})"),
        "severity": "CRITICAL",
        "description": "OpenAI / LLM API Key",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})"),
        "severity": "CRITICAL",
        "description": "Slack Token detected",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PRIVATE) KEY-----"),
        "severity": "CRITICAL",
        "description": "Asymmetric Private Key block detected",
    },
    "GM-SEC-STRIPE-KEY": {
        "pattern": re.compile(r"(sk_live_[0-9a-zA-Z]{24,})"),
        "severity": "CRITICAL",
        "description": "Stripe Live Secret Key detected",
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


class SecretScannerEngine:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def is_whitelisted(self, text: str) -> bool:
        """Determines if a matched pattern is an intentional test mock or placeholder."""
        text_lower = text.lower()
        return any(placeholder in text_lower for placeholder in WHITELIST_PLACEHOLDERS)

    def scan_content(self, content: str, file_path: str = "inline") -> List[SecretFinding]:
        """Scans a text payload line-by-line for secret patterns, supporting robust findings."""
        findings: List[SecretFinding] = []
        lines = content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            for rule_id, rule_info in self.rules.items():
                pattern: re.Pattern = rule_info["pattern"]
                for match in pattern.finditer(line):
                    matched_val = match.group(1) if match.groups() else match.group(0)
                    if not self.is_whitelisted(matched_val):
                        findings.append(
                            SecretFinding(
                                rule_id=rule_id,
                                description=rule_info["description"],
                                file_path=file_path,
                                line_number=line_num,
                                matched_text_masked=mask_secret(matched_val),
                            )
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
        except Exception:
            return []


# Alias for backwards compatibility with any HEAD references
SecretScanner = SecretScannerEngine
