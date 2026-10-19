import logging
from typing import List, Dict, Any
from gossipmesh.repository.chunking import chunk_python_code
from gossipmesh.repository.vector_store import PGVectorStore

logger = logging.getLogger(__name__)


class IncrementalIndexer:
    def __init__(self, vector_store: PGVectorStore, embedding_model=None):
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def index_file(self, filepath: str, content: str, repo_id: int, commit_sha: str):
        if not filepath.endswith(".py"):
            logger.info(f"Skipping non-python file: {filepath}")
            return

        chunks = chunk_python_code(content, filepath)

        for chunk in chunks:
            # We mock the embedding here. In prod, use self.embedding_model.embed(...)
            embedding = [0.0] * 1536

            metadata = {
                "filepath": chunk["filepath"],
                "symbol_name": chunk["symbol_name"],
                "type": chunk["type"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "commit_sha": commit_sha,
                "repo_id": repo_id,
            }

            self.vector_store.upsert(
                id=f"{repo_id}_{filepath}_{chunk['symbol_name']}",
                vector=embedding,
                metadata=metadata,
                content=chunk["content"],
            )

    def remove_file(self, filepath: str, repo_id: int):
        self.vector_store.delete_by_metadata(repo_id=repo_id, filepath=filepath)
