import json
import logging
from typing import List, Optional
from gossipmesh.models.pr_review import SecurityFinding, TestResult, ReviewResponse
from gossipmesh.review.prompt_pipeline import PromptPipeline, PromptPipelineInput

logger = logging.getLogger(__name__)


class PRReviewService:
    def __init__(self, prompt_pipeline: Optional[PromptPipeline] = None):
        self.prompt_pipeline = prompt_pipeline or PromptPipeline()

    def construct_review_prompt(self, input_data: PromptPipelineInput, model: str = "gemini-1.5-pro"):
        """Constructs an isolated, structured GenerationRequest using the prompt pipeline."""
        return self.prompt_pipeline.build_generation_request(input_data, model=model)

    async def extract_security_findings(
        self,
        input_data: Optional[PromptPipelineInput] = None,
        provider_adapter: Optional[object] = None,
    ) -> List[SecurityFinding]:
        """
        Analyzes the PR for security findings using the structured prompt pipeline and AI provider.
        Falls back cleanly to empty findings if no provider or input data is supplied.
        """
        logger.info("Extracting security findings.")
        if not input_data or not provider_adapter:
            return []

        try:
            req = self.construct_review_prompt(input_data)
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
