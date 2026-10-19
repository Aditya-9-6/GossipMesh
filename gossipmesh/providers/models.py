from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class GenerationRequest(BaseModel):
    messages: List[Message]
    model: str
    temperature: float = 0.7
    max_tokens: int = 1024
    stop_sequences: Optional[List[str]] = None
    timeout: Optional[float] = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate_usd: float = 0.0


class GenerationResponse(BaseModel):
    content: str
    model: str
    usage: Usage
    raw_response: Optional[Dict[str, Any]] = None


class ProviderHealth(BaseModel):
    is_healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
