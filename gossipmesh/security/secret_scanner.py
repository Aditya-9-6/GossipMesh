import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Regular expression rules for high-confidence secret detection
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "description": "AWS Access Key ID",
        "severity": "HIGH",
    },
    "GM-SEC-JWT": {
        "pattern": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9_-]{10,}"),
        "description": "JSON Web Token (JWT)",
        "severity": "MEDIUM",
    },
    "GM-SEC-GITHUB-PAT": {
        "pattern": re.compile(r"ghp_[a-zA-Z0-9]{36}"),
        "description": "GitHub Personal Access Token",
        "severity": "CRITICAL",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PRIVATE) KEY-----"),
        "description": "Private Cryptographic Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-SLO-WEBHOOK": {
        "pattern": re.compile(r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]{24}"),
        "description": "Slack Webhook URL",
        "severity": "HIGH",
    },
}


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_text(self, text: str) -> List[Dict[str, Any]]:
        """Scans a text string for secrets, returning a list of findings."""
        findings = []
        for rule_id, rule_info in self.rules.items():
            pattern = rule_info["pattern"]
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "rule_id": rule_id,
                        "description": rule_info["description"],
                        "severity": rule_info["severity"],
                        "matched_text": match.group(0)[:10] + "..." if len(match.group(0)) > 10 else match.group(0),
                    }
                )
        return findings

    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Scans an individual file for secrets."""
        if not file_path.is_file():
            return []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            findings = self.scan_text(content)
            for f in findings:
                f["file_path"] = str(file_path)
            return findings
        except Exception:
            return []

    def scan_git_diff(self, repo_path: str = ".") -> List[Dict[str, Any]]:
        """Scans uncommitted git diffs for secrets."""
        try:
            result = subprocess.run(
                ["git", "diff"],
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            return self.scan_text(result.stdout)
        except Exception:
            return []
