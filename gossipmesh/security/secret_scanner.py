import re
import subprocess
from typing import Dict, List, Optional, Any

SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "description": "AWS Access Key ID",
        "severity": "HIGH",
        "category": "hardcoded_secret",
    },
    "GM-SEC-GITHUB-TOKEN": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})"),
        "description": "GitHub Personal Access Token",
        "severity": "HIGH",
        "category": "hardcoded_secret",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})"),
        "description": "Slack Access Token",
        "severity": "MEDIUM",
        "category": "hardcoded_secret",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----"),
        "description": "Private Cryptographic Key",
        "severity": "CRITICAL",
        "category": "hardcoded_secret",
    },
}


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_text(self, text: str, file_path: str = "") -> List[Dict[str, Any]]:
        findings = []
        lines = text.splitlines()
        for line_num, line in enumerate(lines, 1):
            for rule_id, rule in self.rules.items():
                match = rule["pattern"].search(line)
                if match:
                    findings.append(
                        {
                            "rule_id": rule_id,
                            "description": rule["description"],
                            "severity": rule["severity"],
                            "category": rule["category"],
                            "file_path": file_path,
                            "line_number": line_num,
                            "matched_text": match.group(0)[:6] + "..." if len(match.group(0)) > 6 else "***",
                        }
                    )
        return findings

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
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
                capture_output=True,
                text=True,
                check=True,
            )
            diff_output = result.stdout
            return self.scan_text(diff_output, "git_diff")
        except Exception:
            return []
