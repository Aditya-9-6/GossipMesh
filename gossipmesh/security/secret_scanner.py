"""
High-confidence secret detection and scanner (Task).
Scans files, codebases, and git diffs for leaked secrets such as API keys, tokens, and private keys.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Regular expression rules for high-confidence secret detection
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "severity": "CRITICAL",
        "description": "AWS Access Key ID detected",
    },
    "GM-SEC-GH-TOKEN": {
        "pattern": re.compile(r"(?:^|[^A-Za-z0-9])(ghp_[a-zA-Z0-9]{36})(?:[^A-Za-z0-9]|$)"),
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token detected",
    },
    "GM-SEC-GITHUB-PAT": {
        "pattern": re.compile(r"(?:^|[^A-Za-z0-9])(ghp_[a-zA-Z0-9]{36})(?:[^A-Za-z0-9]|$)"),
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token detected",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})"),
        "severity": "HIGH",
        "description": "Slack Token detected",
    },
    "GM-SEC-RSA-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PRIVATE) KEY-----"),
        "severity": "CRITICAL",
        "description": "Private cryptographic key detected",
    },
    "GM-SEC-STRIPE-KEY": {
        "pattern": re.compile(r"(?:rk|sk)_(?:test|live)_[0-9a-zA-Z]{24,}"),
        "severity": "CRITICAL",
        "description": "Stripe Secret API Key detected",
    },
    "GM-SEC-STRIPE-LIVE": {
        "pattern": re.compile(r"(?:rk|sk)_live_[0-9a-zA-Z]{24,}"),
        "severity": "CRITICAL",
        "description": "Stripe Live API Key detected",
    },
}


def mask_secret(secret: str) -> str:
    if not secret:
        return "****"
    if len(secret) <= 8:
        return "****"
    return secret[:4] + "..." + secret[-2:]


class SecretFinding:
    def __init__(
        self,
        rule_id: str,
        severity: str,
        description: str,
        file_path: str,
        line_number: int,
        snippet: str,
        matched_text_masked: Optional[str] = None,
    ):
        self.rule_id = rule_id
        self.severity = severity
        self.description = description
        self.file_path = file_path
        self.line_number = line_number
        self.snippet = snippet
        self.matched_text_masked = matched_text_masked or mask_secret(snippet)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "snippet": self.snippet,
            "matched_text_masked": self.matched_text_masked,
        }


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_text(self, text: str, file_path: str = "<string>") -> List[SecretFinding]:
        findings: List[SecretFinding] = []
        lines = text.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for rule_id, rule_info in self.rules.items():
                pattern = rule_info["pattern"]
                match = pattern.search(line)
                if match:
                    snippet = line.strip()
                    if len(snippet) > 80:
                        snippet = snippet[:80] + "..."
                    matched_group = match.group(1) if match.groups() else snippet
                    findings.append(
                        SecretFinding(
                            rule_id=rule_id,
                            severity=rule_info["severity"],
                            description=rule_info["description"],
                            file_path=file_path,
                            line_number=line_idx,
                            snippet=snippet,
                            matched_text_masked=mask_secret(matched_group),
                        )
                    )
        return findings

    def scan_content(self, text: str, file_path: str = "<string>") -> List[SecretFinding]:
        return self.scan_text(text, file_path)

    def scan_file(self, file_path: Path | str) -> List[SecretFinding]:
        path = Path(file_path)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_text(content, str(path))
        except Exception:
            return []

    def scan_directory(self, dir_path: Path | str, exclude_dirs: Optional[List[str]] = None) -> List[SecretFinding]:
        exclude_dirs = exclude_dirs or [".git", "node_modules", "venv", "__pycache__", "dist", "build"]
        root = Path(dir_path)
        if not root.is_dir():
            return []

        all_findings: List[SecretFinding] = []
        for path in root.rglob("*"):
            if any(ex in path.parts for ex in exclude_dirs):
                continue
            if path.is_file():
                all_findings.extend(self.scan_file(path))
        return all_findings


# Alias for compatibility with tests expecting SecretScannerEngine
SecretScannerEngine = SecretScanner
