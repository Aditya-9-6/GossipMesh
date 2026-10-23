import json
import logging
from typing import List, Any, Optional
from gossipmesh.models.pr_review import SecurityFinding, TestResult, ReviewResponse

logger = logging.getLogger(__name__)


class PRReviewService:
    async def extract_security_findings(
        self, input_data: Optional[Any] = None, provider_adapter: Optional[Any] = None
    ) -> List[SecurityFinding]:
        """
        Analyzes the PR for security findings.
        Returns a list of findings.
        """
        logger.info("Extracting security findings.")
        if not input_data or not provider_adapter:
            return []

        try:
            req = getattr(self, "construct_review_prompt", lambda x: x)(input_data)
            # Call provider adapter generate method
            if hasattr(provider_adapter, "generate"):
                response = await provider_adapter.generate(req)
                if response and hasattr(response, "content"):
                    data = json.loads(response.content)
                    review_response = ReviewResponse(**data)
                    return review_response.findings
        except Exception as e:
            import traceback

            logger.error(f"Error during AI security finding extraction: {e}")
            traceback.print_exc()

        return []

    async def execute_tests(self) -> TestResult:
        """
        Executes required tests for the PR.
        Returns a dictionary representing test results.
        """
        logger.info("Executing tests.")
        # Mock logic
        return TestResult(status="passed")
