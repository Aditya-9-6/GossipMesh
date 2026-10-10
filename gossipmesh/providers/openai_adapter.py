from typing import AsyncGenerator
import time
from openai import AsyncOpenAI
import tiktoken

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage

class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str):
        """Create an asynchronous OpenAI client using the supplied API key."""
        super().__init__(api_key)
        self.client = AsyncOpenAI(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        """Return the provider identifier "openai"."""
        return "openai"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Return the first completion's text, reported token usage, and raw response.

        The cost estimate is always zero. SDK and response processing errors
        propagate.
        """
        start_time = time.time()

        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        response = await self.client.chat.completions.create(
            model=request.model,
            messages=formatted_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences
        )

        end_time = time.time()

        usage = Usage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            cost_estimate_usd=0.0 # To be implemented properly via a pricing table
        )

        return GenerationResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage=usage,
            raw_response=response.model_dump()
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Yield nonempty text deltas from the first choice in each streamed chunk.

        SDK and stream processing errors propagate, possibly after yielding text.
        """
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        stream = await self.client.chat.completions.create(
            model=request.model,
            messages=formatted_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences,
            stream=True
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def check_health(self) -> ProviderHealth:
        """Probe the models API and return health with latency in milliseconds.

        Exceptions become an unhealthy result containing the error message.
        """
        start_time = time.time()
        try:
            # simple models query to check auth and network
            await self.client.models.list()
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        """Count tokens with cl100k_base, independently of the requested model.

        Tokenizer errors propagate, including ValueError for disallowed special
        token text.
        """
        # Defaulting to cl100k_base which is used by most modern OpenAI models (GPT-4, 3.5-turbo)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
