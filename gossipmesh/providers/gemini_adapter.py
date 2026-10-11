from typing import AsyncGenerator
import time
import google.generativeai as genai
from google.generativeai import GenerativeModel

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage

class GeminiProvider(BaseProvider):
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

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        start_time = time.time()

        model = genai.GenerativeModel(request.model)
        contents = self._convert_messages(request.messages)

        response = await model.generate_content_async(
            contents,
            generation_config=genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                stop_sequences=request.stop_sequences,
            )
        )

        end_time = time.time()

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

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        model = genai.GenerativeModel(request.model)
        contents = self._convert_messages(request.messages)

        response = await model.generate_content_async(
            contents,
            stream=True,
            generation_config=genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                stop_sequences=request.stop_sequences,
            )
        )
        async for chunk in response:
            yield chunk.text

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            await model.generate_content_async("ping")
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        model = genai.GenerativeModel("gemini-1.5-flash")
        try:
            return model.count_tokens(text).total_tokens
        except:
            return int(len(text.split()) * 1.3)
