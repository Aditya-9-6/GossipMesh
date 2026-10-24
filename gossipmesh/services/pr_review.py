import logging
from typing import List
from gossipmesh.models.pr_review import SecurityFinding, TestResult

logger = logging.getLogger(__name__)


class PRReviewService:
    async def extract_security_findings(self) -> List[SecurityFinding]:
        """
        Analyzes the PR for security findings.
        Returns a list of mock findings.
        """
        logger.info("Extracting security findings.")
        # Mock logic
        return []

    async def execute_tests(self) -> TestResult:
        """
        Executes required tests for the PR.
        Returns a dictionary representing test results.
        """
        logger.info("Executing tests.")
        # Mock logic
        return TestResult(status="passed")
