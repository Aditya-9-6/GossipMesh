import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        "pattern": re.compile(r"(gh[pous]_[a-zA-Z0-9]{36})"),
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token detected",
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


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_content(self, content: str, file_path: str = "inline") -> List[Dict[str, Any]]:
        findings = []
        for rule_id, rule_spec in self.rules.items():
            pattern = rule_spec["pattern"]
            for match in pattern.finditer(content):
                findings.append(
                    {
                        "rule_id": rule_id,
                        "description": rule_spec["description"],
                        "file_path": file_path,
                        "matched": match.group(0),
                    }
                )
        return findings
