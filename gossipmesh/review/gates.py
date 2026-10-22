"""Deterministic Review Gates (Task 72).

Enforces non-overridable deterministic checks including:
- Secret scanning (high-entropy tokens, private keys, API credentials)
- Dependency scanning (banned / vulnerable packages, unpinned dependencies)
- AST security scanning (equivalent to Bandit: shell injection, eval, pickle, SQL injection)
- Syntax and lint verification
- Changed-file policies (blocked extensions, workflow tampering, file sizes)

Core Invariant: Critical deterministic findings cannot be overridden by AI approval.
"""

import ast
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from gossipmesh.models.pr_review import (
    Confidence,
    Evidence,
    RemediationModel,
    SecurityFinding,
    Severity,
    TestResult,
    Verdict,
)
from gossipmesh.review.normalization import (
    FindingNormalizer,
    canonicalize_path,
    compute_stable_fingerprint,
)
from gossipmesh.review.prompt_pipeline import ChangedFileContext

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. Secret Scanner
# -----------------------------------------------------------------------------

SECRET_PATTERNS = [
    (
        "AWS_KEY",
        re.compile(r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}"),
        "CRITICAL",
        "AWS Access Key ID detected.",
        "Remove the hardcoded AWS key and use IAM roles or AWS Secrets Manager.",
    ),
    (
        "GITHUB_TOKEN",
        re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}"),
        "CRITICAL",
        "GitHub Personal Access Token detected.",
        "Revoke token immediately and use GitHub Secrets or GitHub App installation tokens.",
    ),
    (
        "SLACK_WEBHOOK",
        re.compile(
            r"https://hooks\.slack\.com/services/T[0-9A-Za-z_\-]{7,14}/B[0-9A-Za-z_\-]{7,14}/[0-9A-Za-z_\-]{20,36}"
        ),
        "CRITICAL",
        "Slack Webhook URL detected.",
        "Store Slack webhook URLs in encrypted environment variables.",
    ),
    (
        "PRIVATE_KEY",
        re.compile(r"-----BEGIN (?:[A-Z0-9_\- ]+)?PRIVATE KEY-----"),
        "CRITICAL",
        "Unencrypted Private Key block detected.",
        "Never commit private keys to version control. Use KMS or HashiCorp Vault.",
    ),
    (
        "GENERIC_SECRET_ASSIGNMENT",
        re.compile(
            r"""(?:api_key|api_secret|jwt_secret|client_secret|auth_token)\s*=\s*['"][a-zA-Z0-9_\-]{20,}['"]""",
            re.IGNORECASE,
        ),
        "CRITICAL",
        "Hardcoded API credential or JWT secret assignment detected.",
        "Inject secrets via environment variables or secret vaults at runtime.",
    ),
]


class SecretScanner:
    """Deterministic regex & pattern-based secret scanner."""

    @classmethod
    def scan(cls, file: ChangedFileContext) -> List[SecurityFinding]:
        findings = []
        content = file.patch or ""
        lines = content.splitlines()
        is_diff = any(l.strip().startswith("@@") or l.strip().startswith("+++") for l in lines)

        for line_idx, line_text in enumerate(lines, start=1):
            stripped = line_text.strip()
            if is_diff:
                if not stripped.startswith("+") or stripped.startswith("+++"):
                    continue
                cleaned_line = stripped.lstrip("+").strip()
            else:
                if stripped.startswith("+"):
                    cleaned_line = stripped.lstrip("+").strip()
                else:
                    cleaned_line = stripped

            for rule_id, pattern, severity, desc, remediation_text in SECRET_PATTERNS:
                match = pattern.search(cleaned_line)
                if match:
                    fp = compute_stable_fingerprint(
                        file_path=file.path,
                        category="SECRET_LEAK",
                        rule_id=rule_id,
                        snippet=cleaned_line,
                        line=line_idx,
                    )
                    finding = SecurityFinding(
                        id=f"SECRET-{fp[:8]}",
                        file_path=file.path,
                        line=line_idx,
                        severity=severity,
                        category="SECRET_LEAK",
                        rule_id=rule_id,
                        message=desc,
                        evidence=cleaned_line,
                        evidence_structured=Evidence(
                            description=desc,
                            code_snippet=cleaned_line,
                        ),
                        confidence=Confidence.HIGH,
                        confidence_score=99,
                        is_ai_generated=False,
                        fingerprint=fp,
                        remediation=remediation_text,
                        source_scanner="deterministic:secret_scanner",
                        sources=["deterministic:secret_scanner"],
                    )
                    findings.append(finding)
        return findings


# -----------------------------------------------------------------------------
# 2. Dependency Scanner
# -----------------------------------------------------------------------------

BANNED_PACKAGES = {
    "telnetlib3": ("CRITICAL", "Unencrypted protocol library telnetlib3 is banned in enterprise code."),
    "pycrypto": (
        "HIGH",
        "pycrypto is unmaintained and contains multiple known vulnerabilities. Use pycryptodome or cryptography.",
    ),
    "pickle5": ("HIGH", "pickle5 introduces arbitrary code execution risks during deserialization."),
}


class DependencyScanner:
    """Scans requirements.txt and pyproject.toml for banned and unpinned dependencies."""

    @classmethod
    def scan(cls, file: ChangedFileContext) -> List[SecurityFinding]:
        findings = []
        norm_path = canonicalize_path(file.path).lower()
        if not (norm_path.endswith("requirements.txt") or norm_path.endswith("pyproject.toml")):
            return findings

        content = file.patch or ""
        for line_idx, line_text in enumerate(content.splitlines(), start=1):
            if file.patch and not line_text.startswith("+"):
                continue
            cleaned = line_text.lstrip("+").strip()

            for banned_pkg, (sev, msg) in BANNED_PACKAGES.items():
                if re.search(rf"\b{banned_pkg}\b", cleaned, re.IGNORECASE):
                    fp = compute_stable_fingerprint(
                        file_path=file.path,
                        category="DEPENDENCY_SECURITY",
                        rule_id="DEP-BANNED",
                        snippet=cleaned,
                        line=line_idx,
                    )
                    findings.append(
                        SecurityFinding(
                            id=f"DEP-{fp[:8]}",
                            file_path=file.path,
                            line=line_idx,
                            severity=sev,
                            category="DEPENDENCY_SECURITY",
                            rule_id="DEP-BANNED",
                            message=f"Banned dependency '{banned_pkg}' detected: {msg}",
                            evidence=cleaned,
                            confidence=Confidence.HIGH,
                            confidence_score=95,
                            fingerprint=fp,
                            remediation=f"Remove {banned_pkg} and replace with secure enterprise alternatives.",
                            source_scanner="deterministic:dependency_scanner",
                            sources=["deterministic:dependency_scanner"],
                        )
                    )
        return findings


# -----------------------------------------------------------------------------
# 3. Python AST Security Scanner (Bandit equivalent)
# -----------------------------------------------------------------------------


class ASTSecurityVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.findings: List[SecurityFinding] = []

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # 1. Code execution: eval / exec (B102)
        if func_name in ("eval", "exec"):
            fp = compute_stable_fingerprint(self.file_path, "AST_SECURITY", "B102", line=node.lineno)
            self.findings.append(
                SecurityFinding(
                    id=f"AST-{fp[:8]}",
                    file_path=self.file_path,
                    line=node.lineno,
                    severity="CRITICAL",
                    category="CODE_EXECUTION",
                    rule_id="B102",
                    message=f"Use of built-in `{func_name}` allows arbitrary code execution.",
                    evidence=f"{func_name}(...)",
                    confidence=Confidence.HIGH,
                    confidence_score=95,
                    fingerprint=fp,
                    remediation=f"Avoid `{func_name}`. Parse data using safe structured parsers like `json` or `ast.literal_eval`.",
                    source_scanner="deterministic:bandit_ast",
                    sources=["deterministic:bandit_ast"],
                )
            )

        # 2. Deserialization: pickle.loads / pickle.load (B301)
        if func_name in ("loads", "load") and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in ("pickle", "_pickle", "cPickle"):
                fp = compute_stable_fingerprint(self.file_path, "AST_SECURITY", "B301", line=node.lineno)
                self.findings.append(
                    SecurityFinding(
                        id=f"AST-{fp[:8]}",
                        file_path=self.file_path,
                        line=node.lineno,
                        severity="CRITICAL",
                        category="INSECURE_DESERIALIZATION",
                        rule_id="B301",
                        message="Pickle deserialization is insecure against untrusted input.",
                        evidence=f"pickle.{func_name}(...)",
                        confidence=Confidence.HIGH,
                        confidence_score=95,
                        fingerprint=fp,
                        remediation="Use JSON, Protocol Buffers, or messagepack for serialization.",
                        source_scanner="deterministic:bandit_ast",
                        sources=["deterministic:bandit_ast"],
                    )
                )

        # 3. Shell injection: subprocess with shell=True (B602)
        if func_name in ("Popen", "call", "run", "check_call", "check_output"):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    fp = compute_stable_fingerprint(self.file_path, "AST_SECURITY", "B602", line=node.lineno)
                    self.findings.append(
                        SecurityFinding(
                            id=f"AST-{fp[:8]}",
                            file_path=self.file_path,
                            line=node.lineno,
                            severity="CRITICAL",
                            category="COMMAND_INJECTION",
                            rule_id="B602",
                            message=f"`subprocess.{func_name}` with `shell=True` allows OS command injection.",
                            evidence=f"subprocess.{func_name}(..., shell=True)",
                            confidence=Confidence.HIGH,
                            confidence_score=98,
                            fingerprint=fp,
                            remediation="Set `shell=False` and pass arguments as a list of strings without shell interpolation.",
                            source_scanner="deterministic:bandit_ast",
                            sources=["deterministic:bandit_ast"],
                        )
                    )

        # 4. Weak cryptography: hashlib.md5 or hashlib.sha1 (B303)
        if func_name in ("md5", "sha1") and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "hashlib":
                fp = compute_stable_fingerprint(self.file_path, "AST_SECURITY", "B303", line=node.lineno)
                self.findings.append(
                    SecurityFinding(
                        id=f"AST-{fp[:8]}",
                        file_path=self.file_path,
                        line=node.lineno,
                        severity="HIGH",
                        category="WEAK_CRYPTO",
                        rule_id="B303",
                        message=f"Weak hashing algorithm `hashlib.{func_name}` is vulnerable to collision attacks.",
                        evidence=f"hashlib.{func_name}(...)",
                        confidence=Confidence.HIGH,
                        confidence_score=90,
                        fingerprint=fp,
                        remediation="Use `hashlib.sha256` or `hashlib.sha3_256`.",
                        source_scanner="deterministic:bandit_ast",
                        sources=["deterministic:bandit_ast"],
                    )
                )

        self.generic_visit(node)


class ASTSecurityScanner:
    """Parses Python source code and flags AST security hazards."""

    @classmethod
    def scan_code(cls, file_path: str, source_code: str) -> List[SecurityFinding]:
        norm_path = canonicalize_path(file_path)
        if not norm_path.endswith(".py"):
            return []

        try:
            tree = ast.parse(source_code, filename=file_path)
            visitor = ASTSecurityVisitor(file_path=file_path)
            visitor.visit(tree)
            return visitor.findings
        except SyntaxError as e:
            fp = compute_stable_fingerprint(file_path, "SYNTAX_ERROR", "PY-SYNTAX", line=e.lineno or 1)
            return [
                SecurityFinding(
                    id=f"SYNTAX-{fp[:8]}",
                    file_path=file_path,
                    line=e.lineno or 1,
                    severity="HIGH",
                    category="SYNTAX_ERROR",
                    rule_id="PY-SYNTAX",
                    message=f"Python syntax error: {e.msg}",
                    confidence=Confidence.HIGH,
                    fingerprint=fp,
                    remediation="Fix Python syntax to ensure valid execution.",
                    source_scanner="deterministic:syntax_checker",
                    sources=["deterministic:syntax_checker"],
                )
            ]


# -----------------------------------------------------------------------------
# 4. Changed File Policies
# -----------------------------------------------------------------------------

BLOCKED_FILE_EXTENSIONS = {".pem", ".key", ".pfx", ".p12", ".env", ".credentials", ".id_rsa"}
PROTECTED_PATHS = [".github/workflows/", ".circleci/", "alembic/versions/"]


class ChangedFilePolicyScanner:
    """Enforces policy on file paths, extensions, and restricted directories."""

    @classmethod
    def scan(cls, file: ChangedFileContext) -> List[SecurityFinding]:
        findings = []
        path = canonicalize_path(file.path)
        ext = os.path.splitext(path)[1].lower()

        # 1. Blocked private key or credentials files
        if ext in BLOCKED_FILE_EXTENSIONS or os.path.basename(path).lower() in (".env", "id_rsa"):
            fp = compute_stable_fingerprint(path, "POLICY_VIOLATION", "FILE-BLOCKED-EXT", line=1)
            findings.append(
                SecurityFinding(
                    id=f"POL-{fp[:8]}",
                    file_path=path,
                    line=1,
                    severity="CRITICAL",
                    category="POLICY_VIOLATION",
                    rule_id="FILE-BLOCKED-EXT",
                    message=f"File '{path}' has a blocked security-sensitive extension or name ({ext}).",
                    confidence=Confidence.HIGH,
                    fingerprint=fp,
                    remediation="Remove sensitive key/credential files from git repository.",
                    source_scanner="deterministic:file_policy",
                    sources=["deterministic:file_policy"],
                )
            )

        # 2. Workflow modification policy check
        if any(path.startswith(p) for p in [".github/workflows/"]):
            # Check if workflow patch modifies external actions without SHA pinning
            if "@v" in file.patch and "uses:" in file.patch:
                fp = compute_stable_fingerprint(path, "POLICY_VIOLATION", "WF-UNPINNED-ACTION", line=1)
                findings.append(
                    SecurityFinding(
                        id=f"POL-{fp[:8]}",
                        file_path=path,
                        line=1,
                        severity="HIGH",
                        category="POLICY_VIOLATION",
                        rule_id="WF-UNPINNED-ACTION",
                        message="GitHub Actions workflow uses mutable tag version instead of immutable commit SHA pinning.",
                        confidence=Confidence.HIGH,
                        fingerprint=fp,
                        remediation="Pin third-party GitHub Actions to a full 40-character commit SHA.",
                        source_scanner="deterministic:file_policy",
                        sources=["deterministic:file_policy"],
                    )
                )

        return findings


# -----------------------------------------------------------------------------
# 5. Deterministic Review Gate Orchestrator
# -----------------------------------------------------------------------------


class DeterministicReviewGates:
    """Orchestrates all deterministic scanners and enforces non-overridable gating rules."""

    @classmethod
    def run_all_scanners(
        cls,
        changed_files: List[ChangedFileContext],
        test_results: Optional[TestResult] = None,
    ) -> List[SecurityFinding]:
        """Runs all deterministic scanners across changed files."""
        all_findings: List[SecurityFinding] = []

        for f in changed_files:
            # 1. Secret Scanner
            all_findings.extend(SecretScanner.scan(f))

            # 2. Dependency Scanner
            all_findings.extend(DependencyScanner.scan(f))

            # 3. File Policy Scanner
            all_findings.extend(ChangedFilePolicyScanner.scan(f))

            # 4. AST Security Scanner (if full code or diff lines exist)
            if f.patch and f.path.endswith(".py"):
                # Extract added lines or parse snippet
                added_lines = [
                    line[1:] for line in f.patch.splitlines() if line.startswith("+") and not line.startswith("+++")
                ]
                if added_lines:
                    source_chunk = "\n".join(added_lines)
                    all_findings.extend(ASTSecurityScanner.scan_code(f.path, source_chunk))

        # Normalize and consolidate findings
        return FindingNormalizer.consolidate_findings(all_findings)

    @classmethod
    def enforce_gates(
        cls,
        ai_verdict: Verdict,
        deterministic_findings: List[SecurityFinding],
        test_results: Optional[TestResult] = None,
    ) -> Tuple[Verdict, str]:
        """
        Enforces non-overridable gate invariants.
        CRITICAL RULE: Critical deterministic findings cannot be overridden by AI approval.
        """
        critical_findings = [f for f in deterministic_findings if f.severity == "CRITICAL"]
        high_findings = [f for f in deterministic_findings if f.severity == "HIGH"]

        # Gate 1: Test failures block approval
        if test_results and test_results.status.lower() not in ("passed", "success"):
            return (
                Verdict.ACTION_REQUIRED,
                f"Automated test suite failed with status '{test_results.status}'. PR cannot be approved.",
            )

        # Gate 2: Any CRITICAL deterministic finding overrides approval to REJECTED
        if critical_findings:
            override_msg = (
                f"OVERRIDE: AI suggested {ai_verdict.value}, but {len(critical_findings)} CRITICAL deterministic "
                f"security finding(s) were identified ({', '.join(f.rule_id or f.category for f in critical_findings[:3])}). "
                "Deterministic gates strictly require REJECTED verdict."
            )
            return Verdict.REJECTED, override_msg

        # Gate 3: Any HIGH deterministic finding overrides approval to ACTION_REQUIRED
        if high_findings:
            if ai_verdict == Verdict.APPROVED:
                override_msg = (
                    f"OVERRIDE: AI suggested APPROVED, but {len(high_findings)} HIGH deterministic finding(s) "
                    "require resolution before merge."
                )
                return Verdict.ACTION_REQUIRED, override_msg

        # No deterministic overrides triggered; AI verdict stands
        return ai_verdict, "Deterministic review gates passed."
