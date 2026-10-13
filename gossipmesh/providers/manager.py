from gossipmesh.providers.anthropic_adapter import AnthropicProvider
from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.gemini_adapter import GeminiProvider
from gossipmesh.providers.models import ProviderHealth
from gossipmesh.providers.ollama_adapter import OllamaProvider
from gossipmesh.providers.openai_adapter import OpenAIProvider


class ProviderManager:
    def __init__(self):
        self._providers: dict[str, type[BaseProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
            "ollama": OllamaProvider
        }
        self._instances: dict[str, BaseProvider] = {}

    def register_provider(self, name: str, api_key: str | None = None, **kwargs) -> BaseProvider:
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")

        provider_class = self._providers[name]

        if name == "ollama":
            instance = provider_class(base_url=kwargs.get("base_url", "http://localhost:11434"))
        else:
            if not api_key:
                raise ValueError(f"API key required for {name}")
            instance = provider_class(api_key=api_key)

        self._instances[name] = instance
        return instance

    def get_provider(self, name: str) -> BaseProvider:
        if name not in self._instances:
            raise ValueError(f"Provider {name} not registered. Call register_provider first.")
        return self._instances[name]

    async def check_all_health(self) -> dict[str, ProviderHealth]:
        health_status = {}
        for name, provider in self._instances.items():
            health_status[name] = await provider.check_health()
        return health_status
