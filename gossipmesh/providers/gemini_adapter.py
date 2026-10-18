from typing import AsyncGenerator
import time
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError
from gossipmesh.core.exceptions import ProviderError
from gossipmesh.core.retry import with_retry_and_circuit_breaker, CircuitBreaker

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage

class GeminiProvider(BaseProvider):
    _cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
    def __init__(self, api_key: str):
        super().__init__(api_key)
        # Avoid global state by passing the api_key implicitly via client instances or config overrides
        # Due to google-generativeai SDK limitations, managing multi-tenant keys perfectly without genai.configure
        # requires passing the client explicitly or instantiating a raw HTTPX client.
        # For this milestone, we use the supported client initialization method.
        # Note: The legacy SDK uses global config, the new `google.genai` SDK allows proper client injection.
        genai.configure(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _convert_messages(self, messages):
        converted = []
        for msg in messages:
            role = "user" if msg.role in ["user", "system"] else "model"
            converted.append({"role": role, "parts": [msg.content]})
        return converted

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        time.time()

        model = genai.GenerativeModel(request.model)
        contents = self._convert_messages(request.messages)

        try:
            response = await model.generate_content_async(
                contents,
                generation_config=genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                    stop_sequences=request.stop_sequences,
                ),
                request_options={"timeout": 60.0}
            )
        except GoogleAPIError as e:
            raise ProviderError("Provider API error") from None

        time.time()

        usage = Usage(
            prompt_tokens=self.count_tokens(" ".join([m.content for m in request.messages])),
            completion_tokens=self.count_tokens(response.text),
            total_tokens=0,
            cost_estimate_usd=0.0
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens

        return GenerationResponse(
            content=response.text,
            model=request.model,
            usage=usage,
            raw_response={"prompt_feedback": str(response.prompt_feedback)}
        )

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]: # type: ignore
        model = genai.GenerativeModel(request.model)
        contents = self._convert_messages(request.messages)

        try:
            response = await model.generate_content_async(
                contents,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                    stop_sequences=request.stop_sequences,
                ),
                request_options={"timeout": 60.0}
            )
            async for chunk in response:
                yield chunk.text
        except GoogleAPIError as e:
            raise ProviderError("Provider API error") from None

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            await model.generate_content_async("ping", request_options={"timeout": 60.0})
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error="Provider connection failed")

    def count_tokens(self, text: str) -> int:
        model = genai.GenerativeModel("gemini-1.5-flash")
        try:
            return model.count_tokens(text).total_tokens
        except:
            return int(len(text.split()) * 1.3)
