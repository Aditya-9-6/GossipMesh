import unittest
from unittest.mock import MagicMock, patch
import asyncio

from gossipmesh.agents.llm import LocalLlamaFallback, LLAMA_CPP_AVAILABLE


class TestLocalLlamaFallback(unittest.TestCase):
    def setUp(self):
        self.fallback = LocalLlamaFallback(model_path="dummy.gguf")

    @patch("gossipmesh.agents.llm.Llama")
    @patch("gossipmesh.agents.llm.LLAMA_CPP_AVAILABLE", True)
    def test_generate_completion_success(self, mock_llama_class):
        mock_instance = MagicMock()
        mock_instance.return_value = {"choices": [{"text": "Hello from local fallback!"}]}
        mock_llama_class.return_value = mock_instance
        self.fallback._model = mock_instance

        res = self.fallback.generate_completion("test prompt")
        self.assertEqual(res, "Hello from local fallback!")

    @patch("gossipmesh.agents.llm.Llama")
    @patch("gossipmesh.agents.llm.LLAMA_CPP_AVAILABLE", True)
    def test_gemini_success_no_fallback(self, mock_llama_class):
        async def mock_gemini():
            return "Gemini success response"

        async def run_test():
            return await self.fallback.generate_with_gemini_fallback(
                mock_gemini, prompt_fallback_text="fallback prompt"
            )

        res = asyncio.run(run_test())
        self.assertEqual(res, "Gemini success response")
        mock_llama_class.assert_not_called()

    @patch("gossipmesh.agents.llm.Llama")
    @patch("gossipmesh.agents.llm.LLAMA_CPP_AVAILABLE", True)
    def test_gemini_failure_triggers_fallback(self, mock_llama_class):
        async def mock_gemini_fail():
            raise RuntimeError("Rate limit exceeded (429)")

        mock_instance = MagicMock()
        mock_instance.return_value = {"choices": [{"text": "Local LLM fallback response"}]}
        mock_llama_class.return_value = mock_instance
        self.fallback._model = mock_instance

        async def run_test():
            return await self.fallback.generate_with_gemini_fallback(
                mock_gemini_fail, prompt_fallback_text="fallback prompt"
            )

        res = asyncio.run(run_test())
        self.assertEqual(res, "Local LLM fallback response")


if __name__ == "__main":
    unittest.main()
