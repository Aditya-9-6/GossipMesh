"""
GossipMesh Infrastructure-Aware Security & Architecture Reviewer
================================================================
Scans Infrastructure-as-Code (Terraform, CloudFormation, Dockerfiles,
CI/CD workflows, Kubernetes) for security misconfigurations, hardcoded
credentials, network exposures, and architectural weaknesses.

Produces a deterministic Infrastructure Score (0-100) and actionable
remediation guidance.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class InfrastructureFinding:
    def __init__(
        self,
        rule_id: str,
        severity: str,
        file_path: str,
        line_number: int,
        message: str,
        remediation: str,
    ):
        self.rule_id = rule_id
        self.severity = severity.lower()  # critical, high, medium, low
        self.file_path = file_path
        self.line_number = line_number
        self.message = message
        self.remediation = remediation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "file": self.file_path,
            "line": self.line_number,
            "message": self.message,
            "remediation": self.remediation,
        }


SEVERITY_WEIGHTS = {
    "critical": 15,
    "high": 10,
    "medium": 5,
    "low": 2,
}

# Regex patterns for infrastructure security rules
PATTERNS = {
    "INFRA-SEC-001": {
        "name": "Hardcoded Secret or Private Key",
        "severity": "critical",
        "regex": re.compile(
            r"(?i)(?:password|secret_key|private_key|api_key|token|access_key)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{8,}['\"]|"
            r"-----BEGIN (?:RSA|OPENSSH|EC|DSA)? PRIVATE KEY-----"
        ),
        "remediation": "Move secrets to an environment variable, Vault, or KMS secret store. Do not commit plaintext credentials.",
    },
    "INFRA-SEC-002": {
        "name": "Unrestricted Ingress Exposure (0.0.0.0/0)",
        "severity": "high",
        "regex": re.compile(r"(?i)(?:cidr_blocks|cidr_ip|cidr)\s*=\s*\[?['\"]0\.0\.0\.0/0['\"]"),
        "remediation": "Restrict CIDR blocks to specific corporate VPN or VPC subnets instead of wide-open internet 0.0.0.0/0.",
    },
    "INFRA-SEC-003": {
        "name": "Wildcard IAM Policy Permission",
        "severity": "high",
        "regex": re.compile(r"(?i)['\"](?:Action|Resource)['\"]\s*:\s*(?:['\"]\*['\"]|\[\s*['\"]\*['\"])"),
        "remediation": "Follow principle of least privilege. Grant explicit action and resource ARNs instead of wildcards.",
    },
    "INFRA-DOCKER-001": {
        "name": "Docker Base Image Using ':latest' Tag or Untagged",
        "severity": "medium",
        "regex": re.compile(r"(?i)^FROM\s+[a-zA-Z0-9_\/\-\.]+(?::latest|\s*$)", re.MULTILINE),
        "remediation": "Pin base images to an immutable digest (sha256:...) or specific semantic version tag (e.g. :3.12-slim).",
    },
    "INFRA-DOCKER-002": {
        "name": "Docker Container Missing Non-Root User",
        "severity": "medium",
        "check": "missing_user",
        "remediation": "Add 'USER nonroot' or 'USER 1000' directive before ENTRYPOINT/CMD to prevent root container execution.",
    },
    "INFRA-CICD-001": {
        "name": "CI/CD Action Not Pinned to Commit SHA",
        "severity": "low",
        "regex": re.compile(r"(?i)uses:\s+[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+@(?:v\d+|main|master)"),
        "remediation": "Pin GitHub Actions to full 40-character commit SHAs to prevent supply chain poisoning.",
    },
    "INFRA-K8S-001": {
        "name": "Kubernetes Privileged Container",
        "severity": "critical",
        "regex": re.compile(r"(?i)privileged:\s*true"),
        "remediation": "Set securityContext.privileged to false to prevent container breakout to the host kernel.",
    },
}


def scan_file(file_path: Path, repo_root: Path) -> List[InfrastructureFinding]:
    """Scan a single infrastructure file against known security heuristics."""
    findings: List[InfrastructureFinding] = []
    rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings

    lines = content.splitlines()

    # Rule checks per line
    for line_idx, line in enumerate(lines, start=1):
        # 1. Hardcoded secret
        if PATTERNS["INFRA-SEC-001"]["regex"].search(line):
            # Exclude test files, documentation, or explicit placeholders
            if "dummy" not in line.lower() and "placeholder" not in line.lower() and "test" not in rel_path.lower():
                findings.append(
                    InfrastructureFinding(
                        rule_id="INFRA-SEC-001",
                        severity=PATTERNS["INFRA-SEC-001"]["severity"],
                        file_path=rel_path,
                        line_number=line_idx,
                        message="Potential hardcoded secret or private key detected in configuration.",
                        remediation=PATTERNS["INFRA-SEC-001"]["remediation"],
                    )
                )

        # 2. Open CIDR
        if PATTERNS["INFRA-SEC-002"]["regex"].search(line):
            findings.append(
                InfrastructureFinding(
                    rule_id="INFRA-SEC-002",
                    severity=PATTERNS["INFRA-SEC-002"]["severity"],
                    file_path=rel_path,
                    line_number=line_idx,
                    message="Wide open CIDR block (0.0.0.0/0) detected.",
                    remediation=PATTERNS["INFRA-SEC-002"]["remediation"],
                )
            )

        # 3. Wildcard IAM
        if PATTERNS["INFRA-SEC-003"]["regex"].search(line):
            findings.append(
                InfrastructureFinding(
                    rule_id="INFRA-SEC-003",
                    severity=PATTERNS["INFRA-SEC-003"]["severity"],
                    file_path=rel_path,
                    line_number=line_idx,
                    message="Wildcard IAM action or resource specification detected.",
                    remediation=PATTERNS["INFRA-SEC-003"]["remediation"],
                )
            )

        # 4. CI/CD unpinned actions
        if ".github/workflows" in rel_path or "gitlab-ci" in rel_path:
            if PATTERNS["INFRA-CICD-001"]["regex"].search(line):
                findings.append(
                    InfrastructureFinding(
                        rule_id="INFRA-CICD-001",
                        severity=PATTERNS["INFRA-CICD-001"]["severity"],
                        file_path=rel_path,
                        line_number=line_idx,
                        message="CI/CD action reference pinned to mutable tag rather than full commit SHA.",
                        remediation=PATTERNS["INFRA-CICD-001"]["remediation"],
                    )
                )

        # 5. Kubernetes privileged container
        if PATTERNS["INFRA-K8S-001"]["regex"].search(line):
            findings.append(
                InfrastructureFinding(
                    rule_id="INFRA-K8S-001",
                    severity=PATTERNS["INFRA-K8S-001"]["severity"],
                    file_path=rel_path,
                    line_number=line_idx,
                    message="Kubernetes securityContext specifies privileged: true.",
                    remediation=PATTERNS["INFRA-K8S-001"]["remediation"],
                )
            )

    # Dockerfile specific whole-file checks
    if "dockerfile" in file_path.name.lower():
        # Check latest tag
        for line_idx, line in enumerate(lines, start=1):
            if PATTERNS["INFRA-DOCKER-001"]["regex"].search(line):
                findings.append(
                    InfrastructureFinding(
                        rule_id="INFRA-DOCKER-001",
                        severity=PATTERNS["INFRA-DOCKER-001"]["severity"],
                        file_path=rel_path,
                        line_number=line_idx,
                        message="Base image uses unpinned or :latest tag.",
                        remediation=PATTERNS["INFRA-DOCKER-001"]["remediation"],
                    )
                )

        # Check non-root user
        has_user = any(re.match(r"(?i)^USER\s+\S+", l.strip()) for l in lines)
        if not has_user:
            findings.append(
                InfrastructureFinding(
                    rule_id="INFRA-DOCKER-002",
                    severity=PATTERNS["INFRA-DOCKER-002"]["severity"],
                    file_path=rel_path,
                    line_number=len(lines) or 1,
                    message="Dockerfile does not specify a non-root USER instruction.",
                    remediation=PATTERNS["INFRA-DOCKER-002"]["remediation"],
                )
            )

    return findings


def is_infrastructure_file(p: Path) -> bool:
    """Identify if a file belongs to Infrastructure-as-Code."""
    name = p.name.lower()
    suffix = p.suffix.lower()

    if "dockerfile" in name:
        return True
    if suffix == ".tf" or suffix == ".tfvars":
        return True
    if ".github/workflows" in str(p).replace("\\", "/"):
        return suffix in (".yml", ".yaml")
    if "cloudformation" in str(p).lower() and suffix in (".json", ".yaml", ".yml"):
        return True
    if "k8s" in str(p).lower() and suffix in (".json", ".yaml", ".yml"):
        return True

    return False


def review(
    repo_root: Optional[Path] = None,
    model_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute full infrastructure analysis across the repository.
    Returns calculated score, letter grade, and diagnostic findings.
    """
    root = repo_root or Path.cwd()
    all_findings: List[InfrastructureFinding] = []
    scanned_count = 0

    # Scan infrastructure files
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # Skip node_modules, .git, .venv
        rel_str = str(path).replace("\\", "/")
        if any(skip in rel_str for skip in [".git/", ".venv/", "node_modules/", "__pycache__/"]):
            continue

        if is_infrastructure_file(path):
            scanned_count += 1
            file_findings = scan_file(path, root)
            all_findings.extend(file_findings)

    # Calculate Infrastructure Score
    score = 100
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for f in all_findings:
        sev = f.severity
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        deduction = SEVERITY_WEIGHTS.get(sev, 2)
        score -= deduction

    score = max(0, min(100, score))

    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "files_scanned": scanned_count,
        "total_findings": len(all_findings),
        "severity_summary": severity_counts,
        "findings": [f.to_dict() for f in all_findings],
        "model_used": model_metadata or {"model": "default-heuristics"},
    }


if __name__ == "__main__":
    result = review()
    print(f"Infrastructure Security Score: {result['score']}/100 (Grade: {result['grade']})")
    print(f"Scanned {result['files_scanned']} files. Total findings: {result['total_findings']}")
    for f in result["findings"]:
        print(f"  [{f['severity'].upper()}] {f['file']}:{f['line']} - {f['message']}")
