import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Regular expression rules for high-confidence secret detection
SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "severity": "CRITICAL",
        "description": "AWS Access Key ID detected",
    },
    "GM-SEC-AWS-SECRET": {
        "pattern": re.compile(r"(?:^|[^A-Za-z0-9/+=])([A-Za-z0-9/+=]{40})(?:[^A-Za-z0-9/+=]|$)"),
        "severity": "CRITICAL",
        "description": "Potential AWS Secret Access Key detected",
    },
    "GM-SEC-GITHUB-TOKEN": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36})"),
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token detected",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[a-zA-Z0-9-]{10,48})"),
        "severity": "CRITICAL",
        "description": "Slack Token detected",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"),
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


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_text(self, text: str, source_identifier: str = "inline") -> List[Dict[str, Any]]:
        findings = []
        lines = text.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for rule_id, rule_def in self.rules.items():
                pattern = rule_def["pattern"]
                for match in pattern.finditer(line):
                    findings.append(
                        {
                            "rule_id": rule_id,
                            "severity": rule_def["severity"],
                            "description": rule_def["description"],
                            "source": source_identifier,
                            "line": line_idx,
                            "snippet": line.strip()[:100],
                        }
                    )
        return findings

    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        if not file_path.exists() or not file_path.is_file():
            return []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_text(content, source_identifier=str(file_path))
        except Exception as e:
            logger.error(f"Failed to scan file {file_path}: {e}")
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
