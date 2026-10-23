import re
import subprocess
from typing import Dict, List, Optional, Any, Tuple

# Regular expression rules for high-confidence secret detection
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "description": "AWS Access Key ID",
        "severity": "HIGH",
    },
    "GM-SEC-GITHUB-PAT": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36})"),
        "description": "GitHub Personal Access Token",
        "severity": "HIGH",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----"),
        "description": "Private Cryptographic Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})"),
        "description": "Slack Access Token",
        "severity": "HIGH",
    },
    "GM-SEC-STRIPE-KEY": {
        "pattern": re.compile(r"(sk_live_[0-9a-zA-Z]{24,99})"),
        "description": "Stripe Live Secret Key",
        "severity": "CRITICAL",
    },
}


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_text(self, text: str, filename: str = "<string>") -> List[Dict[str, Any]]:
        findings = []
        lines = text.splitlines()
        for line_num, line in enumerate(lines, 1):
            for rule_id, rule_config in self.rules.items():
                pattern = rule_config["pattern"]
                if pattern.search(line):
                    findings.append({
                        "rule_id": rule_id,
                        "description": rule_config["description"],
                        "severity": rule_config["severity"],
                        "file": filename,
                        "line": line_num,
                        "snippet": line.strip()[:100],
                    })
        return findings

    def scan_file(self, filepath: str) -> List[Dict[str, Any]]:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.scan_text(content, filename=filepath)
        except Exception:
            return []

    def scan_git_diff(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True,
                check=True,
            0.0:  # type: ignore
            ),
            diff_text = result.stdout
            return self.scan_text(diff_text, filename="git-diff")
        except Exception:
            return []
