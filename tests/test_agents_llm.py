import unittest
from unittest.mock import patch, MagicMock
from gossipmesh.agents.llm import LocalLLMFallbackProvider


class TestLocalLLMFallbackProvider(unittest.TestCase):
    @patch("gossipmesh.agents.llm.os.path.exists", return_value=True)
    @patch("gossipmesh.agents.llm.Llama")
    def test_complete_success(self, mock_llama_cls, mock_exists):
        mock_instance = MagicMock()
        mock_instance.return_value = {
            "choices": [{"text": "Hello from local fallback!"}]
        }
        mock_llama_cls.return_value = mock_instance

        provider = LocalLLMFallbackProvider(model_path="dummy.gguf")
        result = provider.complete("Hello test")

        self.assertEqual(result, "Hello from local fallback!")
        mock_llama_cls.assert_called_once()
        mock_instance.assert_called_once()

    @patch("gossipmesh.agents.llm.os.path.exists", return_value=False)
    def test_model_not_found(self, mock_exists):
        provider = LocalLLMFallbackProvider(model_path="nonexistent.gguf")
        with self.assertRaises(FileNotFoundError):
            provider.complete("Test prompt")

    @patch("gossipmesh.agents.llm.os.path.exists", return_value=True)
    @patch("gossipmesh.agents.llm.Llama")
    def test_chat_complete(self, mock_llama_cls, mock_exists):
        mock_instance = MagicMock()
        mock_instance.return_value = {
            "choices": [{"text": "I am a local assistant."}]
        }
        mock_llama_cls.return_value = mock_instance

        provider = LocalLLMFallbackProvider(model_path="dummy.gguf")
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Who are you?"}
        ]
        result = provider.chat_complete(messages)
        self.assertEqual(result, "I am a local assistant.")


if __name__ == "__main__":
    unittest.main()
