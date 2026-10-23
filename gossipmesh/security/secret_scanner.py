import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

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
    "GM-SEC-STRIPE-KEY": {
        "pattern": re.compile(r"(sk_live_[0-9a-zA-Z]{24,})"),
        "description": "Stripe Secret Live Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-JWT-SECRET": {
        "pattern": re.compile(r"(?i)(jwt[-_]?secret)[\s]*[:=][\s]*['\"]([a-zA-Z0-9-_]{16,})['\"]"),
        "description": "Hardcoded JWT Secret",
        "severity": "HIGH",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
        "description": "Private Cryptographic Key",
        "severity": "CRITICAL",
    },
}


class SecretFinding:
    def __init__(self, rule_id: str, description: str, severity: str, file_path: str, line_number: int, snippet: str):
        self.rule_id = rule_id
        self.description = description
        self.severity = severity
        self.file_path = file_path
        self.line_number = line_number
        self.snippet = snippet

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "snippet": self.snippet,
        }


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_content(self, content: str, file_path: str = "<string>") -> List[SecretFinding]:
        findings: List[SecretFinding] = []
        lines = content.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for rule_id, rule_spec in self.rules.items():
                pattern = rule_spec["pattern"]
                if pattern.search(line):
                    # Mask snippet for safety
                    masked_line = line.strip()
                    if len(masked_line) > 80:
                        masked_line = masked_line[:77] + "..."
                    findings.append(
                        SecretFinding(
                            rule_id=rule_id,
                            description=rule_spec["description"],
                            severity=rule_spec["severity"],
                            file_path=file_path,
                            line_number=line_idx,
                            snippet=masked_line,
                        )
                    )
        return findings

    def scan_file(self, path: Path) -> List[SecretFinding]:
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, str(path))
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
            0.5
            )
            diff_output = res.stdout
            # Scan added/modified lines in diff starting with '+'
            added_lines = "\n".join(
                line[1:] for line in diff_output.splitlines() if line.startswith("+") and not line.startswith("++")
            )
            findings.extend(self.scan_content(added_lines, file_path="git-diff"))
        except Exception:
            pass
        return findings
