import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


class LocalLLMFallbackProvider:
    """
    Local LLM fallback completion provider using llama_cpp bindings.
    Ensures autonomous resilience when primary cloud LLM APIs (e.g., Gemini) are rate-limited or unavailable.
    """
    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 2048, n_threads: int = 4):
        self.model_path = model_path or os.getenv("GOSSIPMESH_LOCAL_LLM_PATH", "models/llama-model.gguf")
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._model: Optional[Any] = None
        self._initialized = False

    def _initialize_model(self) -> None:
        if self._initialized:
            return
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Local Llama model weights not found at path: {self.model_path}")
        if Llama is None:
            raise ImportError("llama_cpp is not installed. Please install llama-cpp-python to use local fallback.")
        
        logger.info(f"Loading local Llama model from {self.model_path} with {self.n_threads} threads...")
        self._model = Llama(model_path=self.model_path, n_ctx=self.n_ctx, n_threads=self.n_threads, verbose=False)
        self._initialized = True

    def complete(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7, stop: Optional[List[str]] = None) -> str:
        """
        Generates a text completion using the local Llama model.
        """
        try:
            self._initialize_model()
            if self._model is None:
                raise RuntimeError("Model failed to initialize.")
            response = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or []
            )
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0].get("text", "")
            return ""
        except (FileNotFoundError, ImportError):
            raise
        except Exception as e:
            logger.error(f"Local LLM fallback completion failed: {e}")
            raise RuntimeError(f"Local LLM fallback failed: {e}") from e

    def chat_complete(self, messages: List[Dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        """
        Generates a chat completion given a list of message dicts with role and content.
        """
        formatted_prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_prompt += f"<|{role}|>\n{content}\n"
        formatted_prompt += "<|assistant|>\n"
        return self.complete(prompt=formatted_prompt, max_tokens=max_tokens, temperature=temperature, stop=["<|user|>", "<|system|>"])
