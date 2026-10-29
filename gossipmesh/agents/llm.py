"""Local LLM Fallback Integration via Llama.cpp and Provider Fallback Orchestration.

Provides robust fallback mechanisms when primary providers (such as Gemini or OpenAI)
are rate-limited, unavailable, or encounter errors, ensuring agentic autonomy.
"""

import logging
import time
from typing import Any, AsyncGenerator, List, Optional

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage

logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None  # type: ignore


class LlamaCppProvider(BaseProvider):
    """Local Llama.cpp LLM provider for offline fallback completion."""

    def __init__(self, model_path: str, n_ctx: int = 2048, n_threads: Optional[int] = None):
        super().__init__(api_key="local")
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._model: Optional[Any] = None

    @property
    def provider_name(self) -> str:
        return "llama_cpp"

    def _load_model(self) -> Any:
        if not LLAMA_CPP_AVAILABLE or Llama is None:
            raise RuntimeError("llama_cpp package is not installed. Install with 'pip install llama-cpp-python'.")
        if self._model is None:
            kwargs: dict[str, Any] = {"model_path": self.model_path, "n_ctx": self.n_ctx}
            if self.n_threads is not None:
                kwargs["n_threads"] = self.n_threads
            self._model = Llama(**kwargs)
        return self._model

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        model = self._load_model()
        
        # Format messages into standard prompt format if chat format isn't directly used
        prompt_lines = []
        for msg in request.messages:
            role_prefix = "System" if msg.role == "system" else ("User" if msg.role == "user" else "Assistant")
            prompt_lines.append(f"{role_prefix}: {msg.content}")
        prompt_lines.append("Assistant: ")
        prompt = "\n".join(prompt_lines)

        stop_seqs = request.stop_sequences or ["User:", "System:"]

        start_time = time.time()
        # Run synchronous llama_cpp generation
        output = model(
            prompt,
            max_tokens=request.max_tokens or 512,
            temperature=request.temperature or 0.7,
            stop=stop_seqs,
        )
        generation_time = time.time() - start_time

        text = output["choices"][0]["text"].strip()
        
        prompt_tokens = output.get("usage", {}).get("prompt_tokens", self.count_tokens(prompt))
        completion_tokens = output.get("usage", {}).get("completion_tokens", self.count_tokens(text))
        total_tokens = prompt_tokens + completion_tokens

        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_estimate_usd=0.0,
        )

        return GenerationResponse(
            content=text,
            model=request.model or "llama-cpp-local",
            usage=usage,
            raw_response=output,
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        model = self._load_model()
        prompt_lines = []
        for msg in request.messages:
            role_prefix = "System" if msg.role == "system" else ("User" if msg.role == "user" else "Assistant")
            prompt_lines.append(f"{role_prefix}: {msg.content}")
        prompt_lines.append("Assistant: ")
        prompt = "\n".join(prompt_lines)

        stop_seqs = request.stop_sequences or ["User:", "System:"]

        stream = model(
            prompt,
            max_tokens=request.max_tokens or 512,
            temperature=request.temperature or 0.7,
            stop=stop_seqs,
            stream=True,
        )

        for chunk in stream:
            delta = chunk["choices"][0].get("text", "")
            if delta:
                yield delta

    async def check_health(self) -> ProviderHealth:
        if not LLAMA_CPP_AVAILABLE:
            return ProviderHealth(is_healthy=False, error="llama_cpp not installed")
        try:
            start_time = time.time()
            # Verify model path / loadability
            self._load_model()
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)


class FallbackOrchestratorProvider(BaseProvider):
    """Orchestrates primary providers with automatic fallback to local Llama.cpp."""

    def __init__(self, primary_provider: BaseProvider, fallback_provider: BaseProvider):
        super().__init__(api_key="orchestrator")
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider

    @property
    def provider_name(self) -> str:
        return f"{self.primary_provider.provider_name}_with_fallback_{self.fallback_provider.provider_name}"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        try:
            logger.info(f"Attempting generation with primary provider: {self.primary_provider.provider_name}")
            return await self.primary_provider.generate(request)
        except Exception as primary_error:
            logger.warning(
                f"Primary provider {self.primary_provider.provider_name} failed: {primary_error}. "
                f"Falling back to {self.fallback_provider.provider_name}."
            )
            try:
                return await self.fallback_provider.generate(request)
            except Exception as fallback_error:
                logger.error(f"Fallback provider {self.fallback_provider.provider_name} also failed: {fallback_error}")
                raise primary_error

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        try:
            async for chunk in self.primary_provider.generate_stream(request):
                yield chunk
        except Exception as primary_error:
            logger.warning(
                f"Primary streaming failed ({primary_error}), falling back to {self.fallback_provider.provider_name}"
            )
            async for chunk in self.fallback_provider.generate_stream(request):
                yield chunk

    async def check_health(self) -> ProviderHealth:
        primary_health = await self.primary_provider.check_health()
        if primary_health.is_healthy:
            return primary_health
        logger.info("Primary provider unhealthy, checking fallback health...")
        return await self.fallback_provider.check_health()

    def count_tokens(self, text: str) -> int:
        return self.primary_provider.count_tokens(text)
