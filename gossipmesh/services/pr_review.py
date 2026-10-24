from typing import List, Optional
from gossipmesh.models.pr_review import (
    SecurityFinding,
    TestResultRecord as TestResult,
    ReviewResponse,
    Verdict,
    Severity,
    Confidence,
)


class PRReviewService:
    def __init__(self):
        pass

    def review_pr(self, diff: str) -> ReviewResponse:
        return ReviewResponse(verdict=Verdict.APPROVED, findings=[])
