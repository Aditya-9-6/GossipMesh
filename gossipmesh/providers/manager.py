from typing import Dict, Type, List, Optional
from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.openai_adapter import OpenAIProvider
from gossipmesh.providers.anthropic_adapter import AnthropicProvider
from gossipmesh.providers.gemini_adapter import GeminiProvider
from gossipmesh.providers.ollama_adapter import OllamaProvider
from gossipmesh.providers.models import ProviderHealth

class ProviderManager:
    def __init__(self):
        """Initialize supported provider types and an empty instance registry."""
        self._providers: Dict[str, Type[BaseProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
            "ollama": OllamaProvider
        }
        self._instances: Dict[str, BaseProvider] = {}

    def register_provider(self, name: str, api_key: str | None = None, **kwargs) -> BaseProvider:
        """Create, register, and return a provider, replacing any existing instance.

        Names are case-sensitive. Only Ollama uses base_url from kwargs and
        ignores api_key; other providers require a nonempty key. Raise ValueError
        for unknown names or missing required keys. Initialization errors
        propagate without replacing the registered instance.
        """
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
        """Return a registered instance, raising ValueError if the name is absent."""
        if name not in self._instances:
            raise ValueError(f"Provider {name} not registered. Call register_provider first.")
        return self._instances[name]

    async def check_all_health(self) -> Dict[str, ProviderHealth]:
        """Return health results keyed by registered provider name.

        Checks run sequentially; an empty registry returns an empty dictionary.
        Any exception not handled by a provider's health check propagates.
        """
        health_status = {}
        for name, provider in self._instances.items():
            health_status[name] = await provider.check_health()
        return health_status
