from typing import Any, AsyncGenerator
import time
from openai import AsyncAzureOpenAI
import tiktoken

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage


class AzureOpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, endpoint: str, api_version: str):
        super().__init__(api_key)
        self.endpoint = endpoint
        self.api_version = api_version
        self.client = AsyncAzureOpenAI(api_key=self.api_key, azure_endpoint=self.endpoint, api_version=self.api_version)

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        formatted_messages: list[Any] = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        response = await self.client.chat.completions.create(
            model=request.model,
            messages=formatted_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences,
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
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            # Simple check, list deployments
            await self.client.models.list()
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
