import logging
import time
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None  # type: ignore


class LocalLlamaFallback:
    """Local LLM fallback provider using Llama.cpp bindings for GossipMesh agents."""

    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 2048, n_threads: Optional[int] = None):
        self.model_path = model_path or "model.gguf"
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._model: Optional[Any] = None

    def _load_model(self) -> Any:
        if not LLAMA_CPP_AVAILABLE or Llama is None:
            raise RuntimeError("llama_cpp package is not installed or unavailable.")
        if self._model is None:
            logger.info(f"Loading local Llama.cpp model from {self.model_path}...")
            kwargs: Dict[str, Any] = {"model_path": self.model_path, "n_ctx": self.n_ctx}
            if self.n_threads is not None:
                kwargs["n_threads"] = self.n_threads
            self._model = Llama(**kwargs)
        return self._model

    def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
    ) -> str:
        """Generates a text completion using the local Llama.cpp model."""
        try:
            model = self._load_model()
            response = model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or [],
            )
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0].get("text", "")
            return ""
        except Exception as e:
            logger.error(f"Local Llama.cpp generation failed: {e}")
            raise

    async def generate_with_gemini_fallback(
        self,
        gemini_coroutine_func,
        *args,
        prompt_fallback_text: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        Attempts to execute the primary Gemini coroutine function. If it raises an exception
        (e.g., rate-limited or unavailable), falls back to the local Llama.cpp model.
        """
        try:
            logger.debug("Attempting primary provider generation (Gemini)...")
            return await gemini_coroutine_func(*args, **kwargs)
        except Exception as primary_error:
            logger.warning(
                f"Primary provider (Gemini) failed or rate-limited: {primary_error}. "
                f"Failing over to local Llama.cpp fallback..."
            )
            start_time = time.time()
            result = self.generate_completion(
                prompt=prompt_fallback_text,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            logger.info(f"Local fallback completion generated in {(time.time() - start_time) * 1000:.2f}ms")
            return result
