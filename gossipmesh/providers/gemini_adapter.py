from typing import AsyncGenerator
import time
import google.generativeai as genai

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage

class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str):
        """Configure the shared Gemini SDK with the supplied API key."""
        super().__init__(api_key)
        genai.configure(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        """Return the provider identifier "gemini"."""
        return "gemini"

    def _convert_messages(self, messages):
        """Convert messages to Gemini content entries while preserving their order.

        Map user and system roles to user, and all other roles to model.
        """
        # Google Generative AI typically uses "user" and "model" roles
        converted = []
        for msg in messages:
            role = "user" if msg.role in ["user", "system"] else "model"
            converted.append({"role": role, "parts": [msg.content]})
        return converted

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Return generated text with separately counted prompt and completion usage.

        System messages are treated as user messages. Token counts use the
        count_tokens method's fixed model or fallback, and cost is always zero.
        SDK and response processing errors propagate unless caught by count_tokens.
        """
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

        # approximate usage since gemini python sdk doesn't always return exact usage easily
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
        """Yield Gemini text chunks, treating system messages as user messages.

        SDK and response processing errors propagate, possibly after yielding text.
        """
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
        """Probe Gemini 1.5 Flash with a generation request for "ping".

        Return health with latency in milliseconds; exceptions become an unhealthy
        result containing the error message.
        """
        start_time = time.time()
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            await model.generate_content_async("ping")
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        """Count tokens via Gemini 1.5 Flash, independently of the requested model.

        If the counting call fails, return 1.3 times the whitespace word count,
        rounded down. Model construction errors occur outside this fallback.
        """
        model = genai.GenerativeModel("gemini-1.5-flash")
        try:
            return model.count_tokens(text).total_tokens
        except:
            return int(len(text.split()) * 1.3)
