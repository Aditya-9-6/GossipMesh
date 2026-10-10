"""
Retrieval-Augmented Generation (RAG) system using Vector Embeddings.
Provides a lightweight VectorDB to index and search codebase context for the LLM.
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Tuple
import math

class VectorDB:
    def __init__(self, db_path: str = ".gossip_mesh/vectordb.json"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self.db_path.exists():
            try:
                return json.loads(self.db_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save(self):
        try:
            self.db_path.write_text(json.dumps(self.embeddings), encoding="utf-8")
        except Exception as e:
            print(f"[Warning] Failed to save VectorDB: {e}")

    def get_embedding(self, text: str, api_key: str = "") -> List[float]:
        """Calls Gemini API to get embeddings for the given text."""
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is missing.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["embedding"]["values"]
        except Exception as e:
            print(f"[Warning] Failed to get embedding from Gemini: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2: return 0.0
        if len(vec1) != len(vec2): return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def index_workspace(self, workspace_path: Path):
        """Indexes all .py files in the workspace, skipping tests if necessary."""
        print("[*] Indexing workspace into VectorDB...")
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in [".git", "vendor", ".gossip_mesh", "__pycache__", "node_modules"]]
            for file in files:
                if file.endswith(".py") and not file.startswith("test_"):
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(workspace_path)).replace("\\", "/")

                    try:
                        content = full_path.read_text(encoding="utf-8")
                        # Simple chunking if file is too large (Gemini has high limits, but good to be safe)
                        chunk = content[:15000]
                        embedding = self.get_embedding(chunk)

                        if embedding:
                            self.embeddings[rel_path] = {
                                "content": chunk,
                                "embedding": embedding
                            }
                            print(f"  [+] Indexed: {rel_path}")
                    except Exception as e:
                        print(f"  [!] Failed to index {rel_path}: {e}")
        self.save()
        print(f"[*] Workspace indexing complete. Total files: {len(self.embeddings)}")

    def search(self, query: str, top_k: int = 3, api_key: str = "") -> List[Tuple[str, str, float]]:
        """Searches the VectorDB for the most relevant files based on the query."""
        if not self.embeddings:
            return []

        query_embedding = self.get_embedding(query, api_key)
        if not query_embedding:
            return []

        results = []
        for path, data in self.embeddings.items():
            sim = self._cosine_similarity(query_embedding, data["embedding"])
            results.append((path, data["content"], sim))

        results.sort(key=lambda x: x[2], reverse=True)
        return results[:top_k]
