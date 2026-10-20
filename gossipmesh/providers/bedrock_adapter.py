from typing import AsyncGenerator
import time
import json
import asyncio
boto3 = __import__("boto3")
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from gossipmesh.core.exceptions import ProviderError
from gossipmesh.core.retry import with_retry_and_circuit_breaker, CircuitBreaker

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage


class BedrockProvider(BaseProvider):
    _cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region_name: str = "us-east-1"):
        # We store the access key id as the main "api_key" for BaseProvider compatibility
        super().__init__(aws_access_key_id)
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        _config = Config(retries={'max_attempts': 0}, connect_timeout=10.0, read_timeout=60.0)
        self.client = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=self.api_key,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            config=_config
        )

    @property
    def provider_name(self) -> str:
        return "bedrock"

    def _sync_generate(self, model: str, messages: list, system: list, config: dict):
        return self.client.converse(modelId=model, messages=messages, system=system, inferenceConfig=config)

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        system_prompts = [{"text": msg.content} for msg in request.messages if msg.role == "system"]
        messages = [
            {"role": msg.role, "content": [{"text": msg.content}]} for msg in request.messages if msg.role != "system"
        ]

        config = {
            "maxTokens": request.max_tokens,
            "temperature": request.temperature,
            "stopSequences": request.stop_sequences or [],
        }

        try:
            response = await asyncio.to_thread(
                self._sync_generate,
                request.model,
                messages,
                system_prompts,
                config
            )
        except (ClientError, BotoCoreError) as e:
            raise ProviderError("Provider API error") from None

        usage_data = response.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("inputTokens", 0),
            completion_tokens=usage_data.get("outputTokens", 0),
            total_tokens=usage_data.get("totalTokens", 0),
            cost_estimate_usd=0.0,
        )

        content = response["output"]["message"]["content"][0]["text"]

        return GenerationResponse(content=content, model=request.model, usage=usage, raw_response=response)

    def _sync_generate_stream(self, model: str, messages: list, system: list, config: dict):
        response = self.client.converse_stream(modelId=model, messages=messages, system=system, inferenceConfig=config)
        stream = response.get("stream")
        if stream:
            for event in stream:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"]["delta"]
                    if "text" in delta:
                        yield delta["text"]

    @with_retry_and_circuit_breaker(exceptions=(ProviderError,), circuit_breaker=_cb)
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:  # type: ignore
        system_prompts = [{"text": msg.content} for msg in request.messages if msg.role == "system"]
        messages = [
            {"role": msg.role, "content": [{"text": msg.content}]} for msg in request.messages if msg.role != "system"
        ]

        config = {
            "maxTokens": request.max_tokens,
            "temperature": request.temperature,
            "stopSequences": request.stop_sequences or [],
        }

        loop = asyncio.get_running_loop()

        def consume_generator(gen, q):
            try:
                for item in gen:
                    asyncio.run_coroutine_threadsafe(q.put(item), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(q.put(e), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(None), loop)

        q: asyncio.Queue = asyncio.Queue()

        try:
            gen = self._sync_generate_stream(request.model, messages, system_prompts, config)
            asyncio.create_task(asyncio.to_thread(consume_generator, gen, q))

            while True:
                item = await q.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
        except (ClientError, BotoCoreError) as e:
            raise ProviderError("Provider API error") from None

    def _sync_check_health(self):
        _config = Config(retries={'max_attempts': 0}, connect_timeout=10.0, read_timeout=60.0)
        control_client = boto3.client(
            service_name="bedrock",
            aws_access_key_id=self.api_key,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            config=_config
        )
        control_client.list_foundation_models(byOutputModality="TEXT")
        return True

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            await asyncio.to_thread(self._sync_check_health)
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error="Provider connection failed")

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)
