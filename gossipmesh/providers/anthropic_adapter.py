from typing import AsyncGenerator
import time
from anthropic import AsyncAnthropic, APIError
from gossipmesh.core.exceptions import ProviderError
from gossipmesh.core.retry import with_retry_and_circuit_breaker, CircuitBreaker

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage


class AnthropicProvider(BaseProvider):
    _cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = AsyncAnthropic(api_key=self.api_key, timeout=60.0)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        time.time()

        # Anthropic separates system prompts from the main messages list
        system_prompt = next((msg.content for msg in request.messages if msg.role == "system"), "")
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages if msg.role != "system"]

        try:
            response = await self.client.messages.create(
                model=request.model,
                system=system_prompt,
                messages=messages,  # type: ignore
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stop_sequences=request.stop_sequences or [],
                timeout=request.timeout,
            )
        except APIError as e:
            raise ProviderError("Provider API error") from None

        time.time()

        usage = Usage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            cost_estimate_usd=0.0,
        )

        content = ""
        if response.content:
            content = response.content[0].text  # type: ignore

        return GenerationResponse(
            content=content, model=request.model, usage=usage, raw_response={"id": response.id, "type": response.type}
        )

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:  # type: ignore
        system_prompt = next((msg.content for msg in request.messages if msg.role == "system"), "")
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages if msg.role != "system"]

        try:
            async with self.client.messages.stream(
                model=request.model,
                system=system_prompt,
                messages=messages,  # type: ignore
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stop_sequences=request.stop_sequences or [],
                timeout=request.timeout,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except APIError as e:
            raise ProviderError("Provider API error") from None

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            # simple ping query
            await self.client.messages.create(
                model="claude-3-haiku-20240307", max_tokens=1, messages=[{"role": "user", "content": "hello"}]
            )
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error="Provider connection failed")

    def count_tokens(self, text: str) -> int:
        # Client side token counting for Anthropic is typically done via their API,
        # but for local approximation we can use an average word-to-token ratio
        return int(len(text.split()) * 1.3)
