from typing import AsyncGenerator
import time
from anthropic import AsyncAnthropic

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage

class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str):
        """Create an asynchronous Anthropic client using the supplied API key."""
        super().__init__(api_key)
        self.client = AsyncAnthropic(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        """Return the provider identifier "anthropic"."""
        return "anthropic"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Return the first content block's text and reported token usage.

        Use only the first system message as the system prompt, excluding all
        system messages from the conversation. The cost estimate is zero and
        raw_response contains only the response ID and type. SDK errors and
        errors accessing a non-text content block propagate.
        """
        start_time = time.time()

        # Anthropic separates system prompts from the main messages list
        system_prompt = next((msg.content for msg in request.messages if msg.role == "system"), "")
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages if msg.role != "system"]

        response = await self.client.messages.create(
            model=request.model,
            system=system_prompt,
            messages=messages, # type: ignore
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop_sequences=request.stop_sequences or []
        )

        end_time = time.time()

        usage = Usage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            cost_estimate_usd=0.0
        )

        content = ""
        if response.content:
             content = response.content[0].text # type: ignore

        return GenerationResponse(
            content=content,
            model=request.model,
            usage=usage,
            raw_response={"id": response.id, "type": response.type}
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Yield text chunks using only the first system message as the system prompt.

        All system messages are excluded from the conversation. SDK and stream
        processing errors propagate, possibly after yielding text.
        """
        system_prompt = next((msg.content for msg in request.messages if msg.role == "system"), "")
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages if msg.role != "system"]

        async with self.client.messages.stream(
            model=request.model,
            system=system_prompt,
            messages=messages, # type: ignore
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop_sequences=request.stop_sequences or []
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def check_health(self) -> ProviderHealth:
        """Probe Claude 3 Haiku with a generation request capped at one output token.

        Return health with latency in milliseconds; exceptions become an unhealthy
        result containing the error message.
        """
        start_time = time.time()
        try:
            # simple ping query
            await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "hello"}]
            )
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        """Estimate tokens as 1.3 times the whitespace word count, rounded down."""
        # Client side token counting for Anthropic is typically done via their API,
        # but for local approximation we can use an average word-to-token ratio
        return int(len(text.split()) * 1.3)
