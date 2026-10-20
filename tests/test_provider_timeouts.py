import unittest
from gossipmesh.providers.models import GenerationRequest, Message
from gossipmesh.providers.openai_adapter import OpenAIProvider
from gossipmesh.providers.anthropic_adapter import AnthropicProvider
from gossipmesh.providers.gemini_adapter import GeminiProvider
from gossipmesh.providers.ollama_adapter import OllamaProvider
from unittest.mock import patch, MagicMock, AsyncMock


class TestProviderTimeouts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.request = GenerationRequest(
            messages=[Message(role="user", content="hello")], model="test-model", timeout=15.5
        )

    @patch("gossipmesh.providers.openai_adapter.AsyncOpenAI")
    async def test_openai_timeout_passed(self, mock_openai):
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = AsyncMock()
        mock_openai.return_value = mock_client_instance

        provider = OpenAIProvider(api_key="test")

        # We need to mock the response format
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 1
        mock_response.usage.completion_tokens = 1
        mock_response.usage.total_tokens = 2
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "hi"
        mock_response.model = "test-model"
        mock_response.model_dump.return_value = {}

        mock_client_instance.chat.completions.create.return_value = mock_response

        await provider.generate(self.request)

        mock_client_instance.chat.completions.create.assert_called_once()
        _, kwargs = mock_client_instance.chat.completions.create.call_args
        self.assertEqual(kwargs.get("timeout"), 15.5)

    @patch("gossipmesh.providers.anthropic_adapter.AsyncAnthropic")
    async def test_anthropic_timeout_passed(self, mock_anthropic):
        mock_client_instance = MagicMock()
        mock_client_instance.messages.create = AsyncMock()
        mock_anthropic.return_value = mock_client_instance

        provider = AnthropicProvider(api_key="test")

        mock_response = MagicMock()
        mock_response.usage.input_tokens = 1
        mock_response.usage.output_tokens = 1
        mock_response.content = [MagicMock(text="hi")]
        mock_response.id = "1"
        mock_response.type = "msg"

        mock_client_instance.messages.create.return_value = mock_response

        await provider.generate(self.request)

        mock_client_instance.messages.create.assert_called_once()
        _, kwargs = mock_client_instance.messages.create.call_args
        self.assertEqual(kwargs.get("timeout"), 15.5)

    @patch("gossipmesh.providers.ollama_adapter.httpx.AsyncClient")
    async def test_ollama_timeout_passed(self, mock_httpx_client):
        mock_client_instance = AsyncMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "hi"}, "model": "test"}

        mock_client_instance.post.return_value = mock_response

        # AsyncClient context manager mocking
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_httpx_client.return_value = mock_client_instance

        provider = OllamaProvider()

        await provider.generate(self.request)

        mock_client_instance.post.assert_called_once()
        _, kwargs = mock_client_instance.post.call_args
        self.assertEqual(kwargs.get("timeout"), 15.5)


if __name__ == "__main__":
    unittest.main()
