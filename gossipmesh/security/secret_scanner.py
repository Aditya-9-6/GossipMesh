"""
Production Secret & Credential Scanning Engine (Task 106).

Detects accidental leaks of API keys, private keys, database credentials,
and personal access tokens across source files, test fixtures, configurations,
and review artifacts.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SecretFinding:
    rule_id: str
    description: str
    file_path: Optional[str]
    line_number: int
    matched_text_masked: str
    severity: str = "HIGH"
    filename: Optional[str] = None
    matched_snippet: Optional[str] = None

    def __post_init__(self) -> None:
        if self.filename is None and self.file_path is not None:
            self.filename = self.file_path
        elif self.file_path is None and self.filename is not None:
            self.file_path = self.filename


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
    "GM-SEC-STRIPE-KEY": {
        "pattern": re.compile(r"(sk_live_[0-9a-zA-Z]{24,})"),
        "description": "Stripe Live Secret Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-STRIPE-LIVE": {
        "pattern": re.compile(r"(sk_live_[0-9a-zA-Z]{24,})"),
        "description": "Stripe Live Secret Key",
        "severity": "CRITICAL",
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


def mask_secret(secret: str) -> str:
    """Masks secret keeping only the first 4 and last 2 characters."""
    if not secret or len(secret) <= 8:
        return "****"
    return f"{secret[:4]}...{secret[-2:]}"


class SecretScannerEngine:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def is_whitelisted(self, text: str) -> bool:
        """Determines if a matched pattern is an intentional test mock or placeholder."""
        text_lower = text.lower()
        return any(placeholder in text_lower for placeholder in WHITELIST_PLACEHOLDERS)

    def scan_text(
        self,
        text: str,
        filename: Optional[str] = None,
        source_identifier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        source = filename or source_identifier or "inline"
        findings: List[Dict[str, Any]] = []
        lines = text.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for rule_id, rule_info in self.rules.items():
                pattern = rule_info["pattern"]
                for match in pattern.finditer(line):
                    matched_val = match.group(1) if match.groups() and match.group(1) is not None else match.group(0)
                    if not self.is_whitelisted(matched_val):
                        findings.append(
                            {
                                "rule_id": rule_id,
                                "description": rule_info["description"],
                                "severity": rule_info.get("severity", "HIGH"),
                                "filename": source,
                                "source": source,
                                "line_number": line_idx,
                                "line": line_idx,
                                "matched_snippet": line.strip()[:100],
                                "snippet": line.strip()[:100],
                                "matched_text_masked": mask_secret(matched_val),
                            }
                        )
        return findings

    def scan_diff(self, diff_text: str) -> List[Dict[str, Any]]:
        """Scans a unified diff string for secret leaks."""
        return self.scan_text(diff_text, source_identifier="git-diff")

    def scan_content(self, content: str, file_path: Optional[str] = "inline") -> List[SecretFinding]:
        """Scans a text payload line-by-line for secret patterns returning SecretFinding objects."""
        raw_findings = self.scan_text(content, filename=file_path)
        results = []
        for rf in raw_findings:
            rid = rf["rule_id"]
            if rid == "GM-SEC-STRIPE-KEY":
                rid = "GM-SEC-STRIPE-LIVE"
            results.append(
                SecretFinding(
                    rule_id=rid,
                    description=rf["description"],
                    file_path=rf["filename"],
                    line_number=rf["line_number"],
                    matched_text_masked=rf["matched_text_masked"],
                    severity=rf["severity"],
                    filename=rf["filename"],
                    matched_snippet=rf["matched_snippet"],
                )
            )
        return results

    def scan_file(self, file_path: Path | str) -> List[SecretFinding]:
        """Scans an individual file on disk."""
        p = Path(file_path).resolve()
        try:
            if not p.is_file():
                return []
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

    def scan_directory(self, dir_path: Path | str, exclude_dirs: Optional[List[str]] = None) -> List[SecretFinding]:
        exclude_dirs = exclude_dirs or [".git", "node_modules", "venv", "__pycache__", "dist", "build"]
        findings: List[SecretFinding] = []
        d_path = Path(dir_path)
        if not d_path.is_dir():
            return findings

        for path in d_path.rglob("*"):
            if any(exc in path.parts for exc in exclude_dirs):
                continue
            if path.is_file():
                findings.extend(self.scan_file(path))
        return findings


# Backward compatibility alias
SecretScanner = SecretScannerEngine
