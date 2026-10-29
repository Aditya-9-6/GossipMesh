""Unit tests for GossipMesh local LLM fallback and Llama.cpp integration.""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gossipmesh.agents.llm import LlamaCppProvider, FallbackOrchestratorProvider
from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Message, Usage


class DummyProvider(BaseProvider):
    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(api_key="dummy")
        self._name = name
        self.should_fail = should_fail

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        if self.should_fail:
            raise RuntimeError(f"{self._name} failed intentionally")
        return GenerationResponse(
            content=f"Response from {self._name}",
            model=request.model,
            usage=Usage(prompt_tokens=10, completion_tokens=10, total_tokens=20, cost_estimate_usd=0.0),
            raw_response={},
        )

    async def generate_stream(self, request: GenerationRequest):
        if self.should_fail:
            raise RuntimeError(f"{self._name} stream failed")
        yield f"Stream from {self._name}"

    async def check_health(self) -> ProviderHealth:
        if self.should_fail:
            return ProviderHealth(is_healthy=False, error="unhealthy")
        return ProviderHealth(is_healthy=True, latency_ms=1.0)

    def count_tokens(self, text: str) -> int:
        return len(text.split())


class TestLLMFallbackAndLlamaCpp(unittest.TestCase):
    def setUp(self):
        self.request = GenerationRequest(model="test-model", messages=[Message(role="user", content="Hello local AI")])

    def test_fallback_orchestrator_success_primary(self):
        primary = DummyProvider("primary")
        fallback = DummyProvider("fallback")
        orchestrator = FallbackOrchestratorProvider(primary, fallback)

        import asyncio

        response = asyncio.run(orchestrator.generate(self.request))
        self.assertEqual(response.content, "Response from primary")

    def test_fallback_orchestrator_triggers_fallback(self):
        primary = DummyProvider("primary", should_fail=True)
        fallback = DummyProvider("fallback", should_fail=False)
        orchestrator = FallbackOrchestratorProvider(primary, fallback)

        import asyncio

        response = asyncio.run(orchestrator.generate(self.request))
        self.assertEqual(response.content, "Response from fallback")

    def test_fallback_orchestrator_health(self):
        primary = DummyProvider("primary", should_fail=True)
        fallback = DummyProvider("fallback", should_fail=False)
        orchestrator = FallbackOrchestratorProvider(primary, fallback)

        import asyncio

        health = asyncio.run(orchestrator.check_health())
        self.assertTrue(health.is_healthy)

    @patch("gossipmesh.agents.llm.LLAMA_CPP_AVAILABLE", True)
    @patch("gossipmesh.agents.llm.Llama")
    def test_llama_cpp_provider_generation(self, mock_llama_cls):
        mock_instance = MagicMock()
        mock_instance.return_value = {
            "choices": [{"text": "Local LLM generated response"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        }
        mock_llama_cls.return_value = mock_instance

        provider = LlamaCppProvider(model_path="/path/to/model.gguf")
        import asyncio

        response = asyncio.run(provider.generate(self.request))

        self.assertEqual(response.content, "Local LLM generated response")
        self.assertEqual(response.usage.prompt_tokens, 5)
        mock_llama_cls.assert_called_once_with(model_path="/path/to/model.gguf", n_ctx=2048)

    @patch("gossipmesh.agents.llm.LLAMA_CPP_AVAILABLE", False)
    def test_llama_cpp_not_available(self):
        provider = LlamaCppProvider(model_path="/path/to/model.gguf")
        import asyncio

        with self.assertRaises(RuntimeError):
            asyncio.run(provider.generate(self.request))


if __name__ == "__main__":
    unittest.main()
