from typing import Any, AsyncGenerator
import time
from openai import AsyncOpenAI
import tiktoken

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage


class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        formatted_messages: list[Any] = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        response = await self.client.chat.completions.create(
            model=request.model,
            messages=formatted_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences,
            extra_headers={
                "HTTP-Referer": "https://gossipmesh.io",
                "X-Title": "GossipMesh",
            },
        )

        usage = Usage(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            cost_estimate_usd=0.0,
        )

        return GenerationResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage=usage,
            raw_response=response.model_dump(),
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:  # type: ignore
        formatted_messages: list[Any] = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        stream: Any = await self.client.chat.completions.create(
            model=request.model,
            messages=formatted_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences,
            stream=True,
            extra_headers={
                "HTTP-Referer": "https://gossipmesh.io",
                "X-Title": "GossipMesh",
            },
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            # simple models query to check auth and network
            await self.client.models.list()
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        # Defaulting to cl100k_base which is used by most modern OpenAI models
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
