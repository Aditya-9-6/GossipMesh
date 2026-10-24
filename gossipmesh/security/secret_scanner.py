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
    severity: str = "HIGH"
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "matched_text_masked": self.matched_text_masked,
            "snippet": self.snippet,
        }


# Regular expression rules for high-confidence secret detection
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "description": "AWS Access Key ID",
        "severity": "CRITICAL",
    },
    "GM-SEC-GITHUB-TOKEN": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,})"),
        "description": "GitHub Personal Access Token",
        "severity": "CRITICAL",
    },
    "GM-SEC-GITHUB-PAT": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{36,})"),
        "description": "GitHub Personal Access Token (Extended)",
        "severity": "CRITICAL",
    },
    "GM-SEC-OPENAI-KEY": {
        "pattern": re.compile(r"(sk-(?:live-)?[a-zA-Z0-9_-]{32,})"),
        "description": "OpenAI / LLM API Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-STRIPE-KEY": {
        "pattern": re.compile(r"(sk_live_[0-9a-zA-Z]{24,})"),
        "description": "Stripe Secret Live Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-STRIPE-LIVE": {
        "pattern": re.compile(r"(sk_live_[a-zA-Z0-9]{24,})"),
        "description": "Stripe Live Secret Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-JWT-SECRET": {
        "pattern": re.compile(r"(?i)(jwt[-_]?secret)[\s]*[:=][\s]*['"]([a-zA-Z0-9-_]{16,})['"]"),
        "description": "Hardcoded JWT Secret",
        "severity": "HIGH",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "description": "Private Cryptographic Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})"),
        "description": "Slack Token / Credential",
        "severity": "HIGH",
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

    def scan_content(self, content: str, file_path: str = "<string>") -> List[SecretFinding]:
        """Scans a text payload line-by-line for secret patterns."""
        findings: List[SecretFinding] = []
        lines = content.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for rule_id, rule_spec in self.rules.items():
                pattern = rule_spec["pattern"]
                match = pattern.search(line)
                if match:
                    matched_val = match.group(1) if match.groups() else match.group(0)
                    if not self.is_whitelisted(matched_val):
                        masked_line = line.strip()
                        if len(masked_line) > 80:
                            masked_line = masked_line[:77] + "..."
                        findings.append(
                            SecretFinding(
                                rule_id=rule_id,
                                description=rule_spec["description"],
                                severity=rule_spec.get("severity", "HIGH"),
                                file_path=file_path,
                                line_number=line_idx,
                                matched_text_masked=mask_secret(matched_val),
                                snippet=masked_line,
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

    def scan_directory(self, root_dir: Path, exclude_dirs: Optional[List[str]] = None) -> List[SecretFinding]:
        exclude_dirs = exclude_dirs or [".git", "node_modules", "venv", "__pycache__", "build", "dist"]
        findings: List[SecretFinding] = []

        if not root_dir.exists():
            return findings

        for path in root_dir.rglob("*"):
            if any(ex in path.parts for ex in exclude_dirs):
                continue
            if path.is_file():
                findings.extend(self.scan_file(path))
        return findings

    def scan_git_diff(self, repo_dir: Path) -> List[SecretFinding]:
        findings: List[SecretFinding] = []
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            diff_output = res.stdout
            added_lines = "\n".join(
                line[1:] for line in diff_output.splitlines() if line.startswith("+") and not line.startswith("++")
            )
            findings.extend(self.scan_content(added_lines, file_path="git-diff"))
        except Exception:
            pass
        return findings


# Alias for backwards compatibility if referenced elsewhere as SecretScanner
SecretScanner = SecretScannerEngine
