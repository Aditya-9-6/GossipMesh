from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth

class BaseProvider(ABC):

    def __init__(self, api_key: str):
        """Store the API key for use by provider implementations."""
        self.api_key = api_key

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the string identifier of the provider."""
        pass

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate and return a complete response asynchronously."""
        pass

    @abstractmethod
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Yield response text chunks asynchronously."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Check if the provider is reachable and credentials are valid."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate the number of tokens in the given text."""
        pass
