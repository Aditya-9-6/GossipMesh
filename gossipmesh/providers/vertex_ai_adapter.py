from typing import AsyncGenerator
import time
import json
import vertexai
from google.api_core.exceptions import GoogleAPIError
from gossipmesh.core.exceptions import ProviderError
from gossipmesh.core.retry import with_retry_and_circuit_breaker, CircuitBreaker
from vertexai.generative_models import GenerativeModel, Part, Content

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage


class VertexAIProvider(BaseProvider):
    _cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

    def __init__(self, project_id: str, location: str):
        # BaseProvider expects an api_key, we will pass a placeholder since Vertex uses application default credentials or explicit project info
        super().__init__("vertex_placeholder")
        self.project_id = project_id
        self.location = location
        vertexai.init(project=self.project_id, location=self.location)

    @property
    def provider_name(self) -> str:
        return "vertex_ai"

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        # In Vertex AI (Gemini), system instructions are passed to the model initialization
        system_instruction = next((msg.content for msg in request.messages if msg.role == "system"), None)

        model = GenerativeModel(model_name=request.model, system_instruction=system_instruction)

        contents = []
        for msg in request.messages:
            if msg.role != "system":
                role = "user" if msg.role == "user" else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg.content)]))

        generation_config = {
            "max_output_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stop_sequences": request.stop_sequences,
        }

        try:
            response = await model.generate_content_async(contents=contents, generation_config=generation_config)
        except GoogleAPIError as e:
            raise ProviderError("Provider API error") from None

        usage = Usage(
            prompt_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            completion_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            total_tokens=response.usage_metadata.total_token_count if response.usage_metadata else 0,
            cost_estimate_usd=0.0,
        )

        return GenerationResponse(
            content=response.text or "", model=request.model, usage=usage, raw_response=response.to_dict()
        )

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:  # type: ignore
        system_instruction = next((msg.content for msg in request.messages if msg.role == "system"), None)

        model = GenerativeModel(model_name=request.model, system_instruction=system_instruction)

        contents = []
        for msg in request.messages:
            if msg.role != "system":
                role = "user" if msg.role == "user" else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg.content)]))

        generation_config = {
            "max_output_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stop_sequences": request.stop_sequences,
        }

        try:
            response = await model.generate_content_async(
                contents=contents, generation_config=generation_config, stream=True
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except GoogleAPIError as e:
            raise ProviderError("Provider API error") from None

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            model = GenerativeModel("gemini-1.5-flash-001")
            await model.generate_content_async("ping")
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error="Provider connection failed")

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)
