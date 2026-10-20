from typing import AsyncGenerator
import time
import httpx
import json

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__(api_key="")  # Ollama usually doesn't need an API key
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        time.time()

        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": request.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                        "stop": request.stop_sequences,
                    },
                },
                timeout=request.timeout or 300.0,
            )
            response.raise_for_status()
            data = response.json()

        time.time()

        usage = Usage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            cost_estimate_usd=0.0,
        )

        return GenerationResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", request.model),
            usage=usage,
            raw_response=data,
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:  # type: ignore
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": request.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                        "stop": request.stop_sequences,
                    },
                },
                timeout=request.timeout or 300.0,
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        data = json.loads(chunk)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                response.raise_for_status()
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)
