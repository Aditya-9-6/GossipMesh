import json
import math
import re
from pathlib import Path
from collections import Counter
import hashlib

class SemanticCache:
    def __init__(self, cache_dir: str = ".gossip_mesh/cache", threshold: float = 0.98):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict:
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_metadata(self):
        try:
            self.metadata_file.write_text(json.dumps(self.metadata), encoding="utf-8")
        except Exception:
            pass

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2: return 0.0
        if len(vec1) != len(vec2): return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def get(self, key_text: str) -> dict | None:
        best_match = None
        best_score = 0.0

        from gossipmesh.rag import VectorDB
        db = VectorDB()
        query_embedding = db.get_embedding(key_text)

        if not query_embedding:
            # Fallback to exact match if embedding generation fails
            cache_key = hashlib.sha256(key_text.encode("utf-8")).hexdigest()
            if cache_key in self.metadata:
                 cache_file = self.cache_dir / f"{cache_key}.json"
                 if cache_file.exists():
                     return json.loads(cache_file.read_text(encoding="utf-8"))
            return None

        for cache_key, data in self.metadata.items():
            if isinstance(data, str):
                # Legacy cache format: data is just the key_text string
                # Fallback to exact match string comparison if it's the old format
                if data == key_text:
                    best_match = cache_key
                    best_score = 1.0
                    break
            elif isinstance(data, dict):
                # New cache format
                cached_embedding = data.get("embedding")
                if cached_embedding:
                    score = self._cosine_similarity(query_embedding, cached_embedding)
                    if score > best_score and score >= self.threshold:
                        best_score = score
                        best_match = cache_key

        if best_match:
            print(f"[*] Semantic cache hit! Similarity score: {best_score:.2f}")
            cache_file = self.cache_dir / f"{best_match}.json"
            if cache_file.exists():
                try:
                    return json.loads(cache_file.read_text(encoding="utf-8"))
                except Exception:
                    return None

        return None

    def put(self, key_text: str, value: dict):
        if not isinstance(value, dict):
            # Fallback if value is not dict
            return

        cache_key = hashlib.sha256(key_text.encode("utf-8")).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        from gossipmesh.rag import VectorDB
        db = VectorDB()
        embedding = db.get_embedding(key_text)

        try:
            cache_file.write_text(json.dumps(value), encoding="utf-8")
            self.metadata[cache_key] = {
                "key_text": key_text,
                "embedding": embedding
            }
            self._save_metadata()
        except Exception as e:
            print(f"[Warning] Failed to write cache: {e}")
