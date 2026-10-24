import re
from typing import Dict, List, Optional, Any
from pathlib import Path

SECRET_RULES: Dict[str, Dict[str, Any]] = {
    "GM-SEC-AWS-KEY": {
        "pattern": re.compile(r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        "description": "AWS Access Key ID",
        "severity": "HIGH",
    },
    "GM-SEC-GITHUB-PAT": {
        "pattern": re.compile(r"(ghp_[a-zA-Z0-9]{36})"),
        "description": "GitHub Personal Access Token",
        "severity": "CRITICAL",
    },
    "GM-SEC-SLACK-TOKEN": {
        "pattern": re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})"),
        "description": "Slack Token",
        "severity": "HIGH",
    },
    "GM-SEC-PRIVATE-KEY": {
        "pattern": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"),
        "description": "Private Key Block",
        "severity": "CRITICAL",
    },
    "GM-SEC-STRIPE-KEY": {
        "pattern": re.compile(r"(sk_live_[0-9a-zA-Z]{24,})"),
        "description": "Stripe Live Secret Key",
        "severity": "CRITICAL",
    },
    "GM-SEC-JWT": {
        "pattern": re.compile(r"eyJ[a-zA-Z0-9-_]+\.eyJ[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]+"),
        "description": "JSON Web Token",
        "severity": "MEDIUM",
    },
}


class SecretFinding:
    def __init__(
        self,
        rule_id: str,
        description: str,
        severity: str,
        filename: Optional[str],
        line_number: int,
        matched_snippet: str,
        matched_text_masked: str,
    ):
        self.rule_id = rule_id
        self.description = description
        self.severity = severity
        self.filename = filename
        self.line_number = line_number
        self.matched_snippet = matched_snippet
        self.matched_text_masked = matched_text_masked


def mask_secret(secret: str) -> str:
    if not secret or len(secret) <= 8:
        return "****"
    return f"{secret[:4]}...{secret[-2:]}"


class SecretScanner:
    """Scans codebases, files, and git diffs for leaked secrets."""

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = rules or SECRET_RULES

    def scan_text(self, text: str, filename: Optional[str] = None) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        lines = text.splitlines()
        for line_idx, line in enumerate(lines, start=1):
            for rule_id, rule_info in self.rules.items():
                pattern = rule_info["pattern"]
                matches = pattern.findall(line)
                if matches:
                    matched_val = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    findings.append(
                        {
                            "rule_id": rule_id,
                            "description": rule_info["description"],
                            "severity": rule_info["severity"],
                            "filename": filename,
                            "line_number": line_idx,
                            "matched_snippet": line.strip()[:100],
                            "matched_text_masked": mask_secret(matched_val),
                        }
                    )
        return findings

    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        try:
            if not file_path.is_file():
                return []
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_text(content, filename=str(file_path))
        except Exception:
            return []

    def scan_directory(self, dir_path: Path, exclude_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        exclude_dirs = exclude_dirs or [".git", "node_modules", "venv", "__pycache__", "dist", "build"]
        findings: List[Dict[str, Any]] = []
        if not dir_path.is_dir():
            return findings

        for path in dir_path.rglob("*"):
            if any(exc in path.parts for exc in exclude_dirs):
                continue
            if path.is_file():
                findings.extend(self.scan_file(path))
        return findings


class SecretScannerEngine(SecretScanner):
    def scan_content(self, text: str, file_path: Optional[str] = None) -> List[SecretFinding]:
        raw_findings = self.scan_text(text, filename=file_path)
        results = []
        for rf in raw_findings:
            rid = rf["rule_id"]
            if rid == "GM-SEC-STRIPE-KEY":
                rid = "GM-SEC-STRIPE-LIVE"
            results.append(
                SecretFinding(
                    rule_id=rid,
                    description=rf["description"],
                    severity=rf["severity"],
                    filename=rf["filename"],
                    line_number=rf["line_number"],
                    matched_snippet=rf["matched_snippet"],
                    matched_text_masked=rf["matched_text_masked"],
                )
            )
        return results
