from typing import Dict, Type, List, Any
from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.openai_adapter import OpenAIProvider
from gossipmesh.providers.anthropic_adapter import AnthropicProvider
from gossipmesh.providers.gemini_adapter import GeminiProvider
from gossipmesh.providers.ollama_adapter import OllamaProvider
from gossipmesh.providers.azure_openai_adapter import AzureOpenAIProvider
from gossipmesh.providers.openrouter_adapter import OpenRouterProvider
from gossipmesh.providers.bedrock_adapter import BedrockProvider
from gossipmesh.providers.vertex_ai_adapter import VertexAIProvider
from gossipmesh.providers.models import ProviderHealth


class ProviderManager:
    def __init__(self):
        self._providers: Dict[str, Type[BaseProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
            "ollama": OllamaProvider,
            "azure_openai": AzureOpenAIProvider,
            "openrouter": OpenRouterProvider,
            "bedrock": BedrockProvider,
            "vertex_ai": VertexAIProvider,
        }
        self._instances: Dict[str, BaseProvider] = {}

    def register_provider(self, name: str, api_key: str | None = None, **kwargs: Any) -> BaseProvider:
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")

        provider_class = self._providers[name]

        if name == "ollama":
            instance = provider_class()  # type: ignore
        elif name == "azure_openai":
            if not api_key:
                raise ValueError("API key required for azure_openai")
            endpoint = kwargs.get("endpoint") or kwargs.get("azure_endpoint")
            api_version = kwargs.get("api_version")
            if not endpoint or not api_version:
                raise ValueError("endpoint and api_version required for azure_openai")
            instance = provider_class(api_key=api_key, endpoint=endpoint, api_version=api_version)  # type: ignore
        elif name == "bedrock":
            if not api_key:
                raise ValueError("aws_access_key_id (passed as api_key) required for bedrock")
            aws_secret_access_key = kwargs.get("aws_secret_access_key")
            region_name = kwargs.get("region_name", "us-east-1")
            if not aws_secret_access_key:
                raise ValueError("aws_secret_access_key required for bedrock")
            instance = provider_class(
                aws_access_key_id=api_key, aws_secret_access_key=aws_secret_access_key, region_name=region_name
            )  # type: ignore
        elif name == "vertex_ai":
            project_id = kwargs.get("project_id")
            location = kwargs.get("location", "us-central1")
            if not project_id:
                raise ValueError("project_id required for vertex_ai")
            instance = provider_class(project_id=project_id, location=location)  # type: ignore
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

    async def check_all_health(self) -> Dict[str, ProviderHealth]:
        health_status = {}
        for name, provider in self._instances.items():
            health_status[name] = await provider.check_health()
        return health_status

    def fallback_chain(self, primary: str = "gemini") -> List[BaseProvider]:
        """Return a list of provider instances in order of fallback.

        The primary provider (default 'gemini') is placed first if available,
        followed by all other registered providers.
        """
        chain: List[BaseProvider] = []
        if primary in self._instances:
            chain.append(self._instances[primary])
        for name, provider in self._instances.items():
            if name != primary:
                chain.append(provider)
        return chain
