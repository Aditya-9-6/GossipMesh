"""Finding Normalization and Deduplication Engine (Task 71).

Provides deterministic canonicalization, stable SHA-256 fingerprint generation,
category/severity normalization, evidence structuring, multi-source consolidation,
and intra-run / cross-run deduplication.
"""

from enum import Enum
import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from gossipmesh.models.pr_review import (
    Confidence,
    Evidence,
    Citation,
    RemediationModel,
    SecurityFinding,
    Severity,
)


SEVERITY_RANKS: Dict[str, int] = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}

CONFIDENCE_RANKS: Dict[str, int] = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


def canonicalize_path(path: str) -> str:
    """Canonicalizes file path to forward slashes with stripped leading dots and slashes."""
    if not path:
        return ""
    norm = path.replace("\\", "/").strip()
    norm = re.sub(r"^\.?/+", "", norm)
    norm = re.sub(r"/+", "/", norm)
    return norm


def canonicalize_category(category: Optional[str]) -> str:
    """Normalizes finding category into uppercase standardized token."""
    if not category or not category.strip():
        return "SECURITY"
    clean = category.strip().upper()
    clean = re.sub(r"[\s\-]+", "_", clean)
    return clean


def canonicalize_severity(severity: Optional[Union[str, Severity]]) -> str:
    """Normalizes severity to one of CRITICAL, HIGH, MEDIUM, LOW, INFO."""
    if not severity:
        return "MEDIUM"
    s = severity.value if isinstance(severity, Severity) else str(severity).strip().upper()
    return s if s in SEVERITY_RANKS else "MEDIUM"


def canonicalize_confidence(
    confidence: Optional[Union[str, Confidence]],
    confidence_score: Optional[int] = None,
) -> Tuple[Confidence, int]:
    """Resolves confidence enum and integer score (0-100)."""
    if confidence_score is not None:
        score = max(0, min(100, int(confidence_score)))
        if score >= 80:
            return Confidence.HIGH, score
        elif score >= 50:
            return Confidence.MEDIUM, score
        else:
            return Confidence.LOW, score

    if confidence is not None:
        c_str = confidence.value if isinstance(confidence, Confidence) else str(confidence).strip().upper()
        if c_str == "HIGH":
            return Confidence.HIGH, 90
        elif c_str == "MEDIUM":
            return Confidence.MEDIUM, 60
        elif c_str == "LOW":
            return Confidence.LOW, 30

    return Confidence.MEDIUM, 60


def canonicalize_snippet(snippet: Optional[str]) -> str:
    """Normalizes code snippet to collapse minor whitespace formatting variations."""
    if not snippet or not snippet.strip():
        return ""
    # Collapse multiple whitespace characters/newlines
    cleaned = re.sub(r"\s+", " ", snippet.strip())
    return cleaned


def compute_stable_fingerprint(
    file_path: str,
    category: str,
    rule_id: Optional[str] = None,
    snippet: Optional[str] = None,
    line: int = 1,
    end_line: Optional[int] = None,
) -> str:
    """
    Computes a deterministic SHA-256 fingerprint for a finding.
    Invariant to whitespace differences when snippet is available;
    falls back to canonical line coordinates otherwise.
    """
    c_path = canonicalize_path(file_path)
    c_cat = canonicalize_category(category)
    c_rule = (rule_id or "GENERAL").strip().upper()
    c_snip = canonicalize_snippet(snippet)

    if c_snip:
        raw_token = f"{c_path}:{c_cat}:{c_rule}:{c_snip}"
    else:
        e_line = end_line if end_line is not None and end_line >= line else line
        raw_token = f"{c_path}:{c_cat}:{c_rule}:{line}:{e_line}"

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class FindingNormalizer:
    """Normalizes raw scanner outputs and AI findings, and handles multi-source deduplication."""

    @classmethod
    def normalize_finding(
        cls,
        raw: Union[Dict[str, Any], SecurityFinding],
        default_source: str = "review_engine",
    ) -> SecurityFinding:
        """Normalizes a single finding into a compliant SecurityFinding."""
        if isinstance(raw, SecurityFinding):
            data = raw.model_dump()
        else:
            data = dict(raw)

        # 1. Path & Line coordinates
        file_path = canonicalize_path(
            data.get("file_path") or (data.get("paths", [""])[0] if data.get("paths") else "")
        )
        line = max(1, int(data.get("line") or 1))
        end_line = int(data.get("end_line")) if data.get("end_line") is not None else None
        if end_line is not None and end_line < line:
            end_line = line

        # 2. Category & Rule ID
        category = canonicalize_category(data.get("category"))
        rule_id = data.get("rule_id") or data.get("rule") or data.get("cwe") or data.get("id")

        # 3. Severity & Confidence
        severity = canonicalize_severity(data.get("severity"))
        confidence_enum, confidence_score = canonicalize_confidence(
            data.get("confidence"), data.get("confidence_score")
        )

        # 4. Message & Explanation
        message = data.get("message") or data.get("explanation") or data.get("description") or ""

        # 5. Evidence & Structured Snippet
        snippet = ""
        evidence_structured = data.get("evidence_structured")
        if isinstance(evidence_structured, dict):
            snippet = evidence_structured.get("code_snippet", "")
            citations = [Citation(**c) if isinstance(c, dict) else c for c in evidence_structured.get("citations", [])]
            evidence_model = Evidence(
                description=evidence_structured.get("description", message),
                code_snippet=snippet or None,
                citations=citations or None,
            )
        elif isinstance(evidence_structured, Evidence):
            evidence_model = evidence_structured
            snippet = evidence_model.code_snippet or ""
        else:
            snippet = data.get("code_snippet") or data.get("evidence") or ""
            evidence_model = (
                Evidence(
                    description=message,
                    code_snippet=snippet or None,
                )
                if snippet
                else None
            )

        # 6. Stable Fingerprint
        existing_fp = data.get("fingerprint")
        if not existing_fp:
            fingerprint = compute_stable_fingerprint(
                file_path=file_path,
                category=category,
                rule_id=rule_id,
                snippet=snippet,
                line=line,
                end_line=end_line,
            )
        else:
            fingerprint = existing_fp

        # 7. Remediation
        raw_rem = data.get("remediation")
        remediation: Optional[Union[str, RemediationModel]] = ""
        if isinstance(raw_rem, dict):
            remediation = RemediationModel(**raw_rem)
        elif isinstance(raw_rem, RemediationModel):
            remediation = raw_rem
        elif raw_rem:
            remediation = str(raw_rem)

        # 8. Sources & scanner provenance
        source_scanner = data.get("source_scanner") or default_source
        sources = list(data.get("sources") or [])
        if source_scanner and source_scanner not in sources:
            sources.append(source_scanner)

        finding_id = data.get("id") or f"FINDING-{fingerprint[:8]}"

        return SecurityFinding(
            id=finding_id,
            file_path=file_path,
            line=line,
            end_line=end_line,
            side=data.get("side", "RIGHT"),
            commit_sha=data.get("commit_sha", ""),
            severity=severity,
            category=category,
            rule_id=str(rule_id) if rule_id else None,
            message=message,
            evidence=snippet or (evidence_model.description if evidence_model else None),
            evidence_structured=evidence_model,
            confidence_score=confidence_score,
            confidence=confidence_enum,
            is_ai_generated=data.get("is_ai_generated", False),
            fingerprint=fingerprint,
            remediation=remediation,
            source_scanner=source_scanner,
            sources=sources,
            github_comment_id=data.get("github_comment_id"),
        )

    @classmethod
    def normalize_findings(
        cls,
        findings: List[Union[Dict[str, Any], SecurityFinding]],
        default_source: str = "review_engine",
    ) -> List[SecurityFinding]:
        """Normalizes a list of findings."""
        return [cls.normalize_finding(f, default_source=default_source) for f in findings]

    @classmethod
    def consolidate_findings(
        cls,
        findings: List[SecurityFinding],
        existing_fingerprints: Optional[Set[str]] = None,
    ) -> List[SecurityFinding]:
        """
        Deduplicates and consolidates findings:
        - Drops findings matching existing_fingerprints (cross-run safety).
        - Merges intra-run findings with matching fingerprints into a single finding.
        - Merges finding with highest severity, highest confidence, and combined sources list.
        """
        seen_fps: Set[str] = set(existing_fingerprints or [])
        grouped: Dict[str, List[SecurityFinding]] = {}

        for f in findings:
            if not f.fingerprint:
                f.fingerprint = compute_stable_fingerprint(
                    file_path=f.file_path,
                    category=f.category,
                    rule_id=f.rule_id,
                    snippet=f.evidence_structured.code_snippet if f.evidence_structured else f.evidence,
                    line=f.line,
                    end_line=f.end_line,
                )

            # Check cross-run deduplication
            if f.fingerprint in seen_fps:
                continue

            grouped.setdefault(f.fingerprint, []).append(f)

        consolidated: List[SecurityFinding] = []

        for fp, group in grouped.items():
            if len(group) == 1:
                consolidated.append(group[0])
                continue

            # Merge multiple findings for the same fingerprint
            # 1. Highest severity
            best_sev = max(group, key=lambda x: SEVERITY_RANKS.get(x.severity, 0)).severity

            # 2. Highest confidence
            best_conf_finding = max(
                group,
                key=lambda x: CONFIDENCE_RANKS.get(x.confidence.value if x.confidence else "MEDIUM", 0),
            )
            best_conf = best_conf_finding.confidence
            best_conf_score = best_conf_finding.confidence_score

            # 3. Aggregate all unique sources
            all_sources: List[str] = []
            for item in group:
                for s in item.sources:
                    if s not in all_sources:
                        all_sources.append(s)

            # 4. Longest / richest explanation and evidence
            best_msg = max((item.message for item in group if item.message), key=len, default=group[0].message)
            best_evidence = next((item.evidence_structured for item in group if item.evidence_structured), None)
            best_remediation = next((item.remediation for item in group if item.remediation), group[0].remediation)

            primary = group[0]
            merged = SecurityFinding(
                id=primary.id,
                file_path=primary.file_path,
                line=primary.line,
                end_line=primary.end_line,
                side=primary.side,
                commit_sha=primary.commit_sha,
                severity=best_sev,
                category=primary.category,
                rule_id=primary.rule_id,
                message=best_msg,
                evidence=primary.evidence,
                evidence_structured=best_evidence or primary.evidence_structured,
                confidence_score=best_conf_score,
                confidence=best_conf,
                is_ai_generated=any(item.is_ai_generated for item in group),
                fingerprint=fp,
                remediation=best_remediation,
                source_scanner="consolidated",
                sources=all_sources,
            )
            consolidated.append(merged)

        return consolidated
