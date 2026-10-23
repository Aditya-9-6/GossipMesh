"""Feedback Learning and Evaluation Engine (Task 74).

Manages human feedback persistence (accepted, dismissed, false_positive, reopened, corrected),
evaluates precision/recall/false-positive rates per rule, and safely injects historical feedback
into review prompts while strictly neutralizing prompt injection threats.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from gossipmesh.models.finding_feedback import FindingFeedback, FeedbackType
from gossipmesh.review.prompt_pipeline import (
    FindingStatus,
    HistoricalFindingFeedback,
    PromptPipeline,
)

logger = logging.getLogger(__name__)


class FeedbackLearningEngine:
    """Service for recording human feedback, computing accuracy metrics, and exporting safe prompt context."""

    def __init__(self, db: Session):
        self.db = db

    def record_feedback(
        self,
        organization_id: str,
        repository_id: str,
        finding_fingerprint: str,
        feedback_type: FeedbackType | str,
        user_id: Optional[str] = None,
        user_comment: Optional[str] = None,
        corrected_severity: Optional[str] = None,
        corrected_category: Optional[str] = None,
        file_path: Optional[str] = None,
        rule_id: Optional[str] = None,
    ) -> FindingFeedback:
        """
        Records human feedback on a finding.
        Sanitizes user comment to prevent prompt injection attacks if later referenced.
        """
        # Validate feedback type
        if isinstance(feedback_type, str):
            f_type = feedback_type.upper()
            if f_type not in FeedbackType.__members__:
                raise ValueError(
                    f"Invalid feedback type: {feedback_type}. Must be one of {list(FeedbackType.__members__.keys())}"
                )
        else:
            f_type = feedback_type.value

        # Sanitize comment against prompt injection attempts
        sanitized_comment = PromptPipeline.sanitize_untrusted_text(user_comment or "") if user_comment else None

        record = FindingFeedback(
            organization_id=organization_id,
            repository_id=repository_id,
            finding_fingerprint=finding_fingerprint,
            feedback_type=f_type,
            user_id=user_id,
            user_comment=sanitized_comment,
            corrected_severity=corrected_severity,
            corrected_category=corrected_category,
            file_path=file_path,
            rule_id=rule_id,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_evaluation_metrics(
        self,
        organization_id: str,
        repository_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes review accuracy evaluation metrics based on human feedback:
        - Total reviews evaluated
        - Acceptance rate
        - False positive rate
        - Dismissal rate
        - Rule-level precision breakdown
        """
        query = self.db.query(FindingFeedback).filter(FindingFeedback.organization_id == organization_id)
        if repository_id:
            query = query.filter(FindingFeedback.repository_id == repository_id)

        all_feedback = query.all()
        total = len(all_feedback)

        if total == 0:
            return {
                "total_feedbacks": 0,
                "precision": 1.0,
                "false_positive_rate": 0.0,
                "acceptance_rate": 1.0,
                "dismissal_rate": 0.0,
                "counts_by_type": {},
                "rule_breakdown": {},
            }

        counts: Dict[str, int] = {}
        rule_stats: Dict[str, Dict[str, int]] = {}

        for item in all_feedback:
            t = item.feedback_type
            counts[t] = counts.get(t, 0) + 1

            rule = item.rule_id or "GENERAL"
            if rule not in rule_stats:
                rule_stats[rule] = {"accepted": 0, "false_positive": 0, "dismissed": 0, "total": 0}

            rule_stats[rule]["total"] += 1
            if t == FeedbackType.ACCEPTED.value:
                rule_stats[rule]["accepted"] += 1
            elif t == FeedbackType.FALSE_POSITIVE.value:
                rule_stats[rule]["false_positive"] += 1
            elif t == FeedbackType.DISMISSED.value:
                rule_stats[rule]["dismissed"] += 1

        accepted = counts.get(FeedbackType.ACCEPTED.value, 0)
        false_positives = counts.get(FeedbackType.FALSE_POSITIVE.value, 0)
        dismissed = counts.get(FeedbackType.DISMISSED.value, 0)
        negatives = false_positives + dismissed

        precision = accepted / (accepted + negatives) if (accepted + negatives) > 0 else 1.0
        false_positive_rate = false_positives / total
        acceptance_rate = accepted / total
        dismissal_rate = dismissed / total

        rule_breakdown = {}
        for r_name, r_counts in rule_stats.items():
            r_acc = r_counts["accepted"]
            r_neg = r_counts["false_positive"] + r_counts["dismissed"]
            r_prec = r_acc / (r_acc + r_neg) if (r_acc + r_neg) > 0 else 1.0
            rule_breakdown[r_name] = {
                "total": r_counts["total"],
                "precision": round(r_prec, 3),
                "false_positives": r_counts["false_positive"],
            }

        return {
            "total_feedbacks": total,
            "precision": round(precision, 3),
            "false_positive_rate": round(false_positive_rate, 3),
            "acceptance_rate": round(acceptance_rate, 3),
            "dismissal_rate": round(dismissal_rate, 3),
            "counts_by_type": counts,
            "rule_breakdown": rule_breakdown,
        }

    def export_historical_feedback_for_prompt(
        self,
        organization_id: str,
        repository_id: str,
        limit: int = 50,
    ) -> List[HistoricalFindingFeedback]:
        """
        Exports safe, structured HistoricalFindingFeedback list for PromptPipeline.
        Ensures user feedback reasons are sanitized and cannot manipulate system instructions.
        """
        records = (
            self.db.query(FindingFeedback)
            .filter(
                FindingFeedback.organization_id == organization_id,
                FindingFeedback.repository_id == repository_id,
            )
            .order_by(FindingFeedback.created_at.desc())
            .limit(limit)
            .all()
        )

        results: List[HistoricalFindingFeedback] = []
        for r in records:
            if r.feedback_type in (FeedbackType.DISMISSED.value, FeedbackType.FALSE_POSITIVE.value):
                status = FindingStatus.DISMISSED
            else:
                status = FindingStatus.ACCEPTED

            reason = r.user_comment or (
                "Marked false positive" if r.feedback_type == FeedbackType.FALSE_POSITIVE.value else None
            )

            results.append(
                HistoricalFindingFeedback(
                    fingerprint=r.finding_fingerprint,
                    status=status,
                    file_path=r.file_path,
                    rule_or_category=r.rule_id or r.corrected_category,
                    reason=reason,
                )
            )
        return results
