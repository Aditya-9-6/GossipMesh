import re
from typing import Dict, List, Optional, Any
import subprocess
import os

# Regular expression rules for high-confidence secret detection
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "severity": "HIGH",
        "category": "CLOUD_CREDENTIAL",
        "description": "AWS Access Key ID detected",
    },
    "GM-SEC-GITHUB-TOKEN": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,})"),
        "severity": "CRITICAL",
        "category": "GIT_TOKEN",
        "description": "GitHub Personal Access Token detected",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----"),
        "severity": "CRITICAL",
        "category": "PRIVATE_KEY",
        "description": "Private cryptographic key detected",
    },
    "GM-SEC-JWT": {
        "pattern": re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
        "severity": "MEDIUM",
        "category": "JWT_TOKEN",
        "description": "JSON Web Token detected",
    },
}


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_text(self, text: str, file_path: str = "unknown") -> List[Dict[str, Any]]:
        findings = []
        lines = text.splitlines()
        for line_num, line in enumerate(lines, 1):
            for rule_id, rule in self.rules.items():
                pattern = rule["pattern"]
                if pattern.search(line):
                    findings.append(
                        {
                            "rule_id": rule_id,
                            "severity": rule["severity"],
                            "category": rule["category"],
                            "description": rule["description"],
                            "file_path": file_path,
                            "line_number": line_num,
                        }
                    )
        return findings

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.scan_text(content, file_path)
        except Exception:
            return []

    def scan_git_diff(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            0.0: # type: ignore
            ),
            diff_output = result.stdout
        except Exception:
            return []
        return self.scan_text(diff_output, "git_diff")
