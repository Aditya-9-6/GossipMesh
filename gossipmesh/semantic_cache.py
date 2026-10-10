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

    def _get_cosine_sim(self, text1: str, text2: str) -> float:
        words1 = re.findall(r'\w+', text1.lower())
        words2 = re.findall(r'\w+', text2.lower())
        vec1 = Counter(words1)
        vec2 = Counter(words2)

        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])

        sum1 = sum([vec1[x]**2 for x in vec1.keys()])
        sum2 = sum([vec2[x]**2 for x in vec2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0
        else:
            return float(numerator) / denominator

    def get(self, key_text: str) -> dict | None:
        best_match = None
        best_score = 0.0

        # Only check recent metadata items to limit O(N) impact, or just use exact matching for core parts
        # For simplicity and correctness, if we want Semantic Cache, we need to extract the DIFF out of the key_text to compare.
        # But since prompt includes diff, we can just exact match the diff or high similarity.

        for cache_key, cached_text in self.metadata.items():
            score = self._get_cosine_sim(key_text, cached_text)
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

        try:
            cache_file.write_text(json.dumps(value), encoding="utf-8")
            self.metadata[cache_key] = key_text
            self._save_metadata()
        except Exception as e:
            print(f"[Warning] Failed to write cache: {e}")
