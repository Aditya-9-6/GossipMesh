from abc import ABC, abstractmethod
from typing import AsyncGenerator
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth


class BaseProvider(ABC):
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the string identifier of the provider."""
        pass

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a response synchronously (wrapped in async)."""
        pass

    @abstractmethod
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Stream a response."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Check if the provider is reachable and credentials are valid."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate the number of tokens in the given text."""
        pass
