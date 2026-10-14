from typing import Any

from pydantic import BaseModel


class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class GenerationRequest(BaseModel):
    messages: list[Message]
    model: str
    temperature: float = 0.7
    max_tokens: int = 1024
    stop_sequences: list[str] | None = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate_usd: float = 0.0


class GenerationResponse(BaseModel):
    content: str
    model: str
    usage: Usage
    raw_response: dict[str, Any] | None = None


class ProviderHealth(BaseModel):
    is_healthy: bool
    latency_ms: float | None = None
    error: str | None = None
