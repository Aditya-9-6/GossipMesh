import logging
from typing import List, Dict, Any
from gossipmesh.repository.chunking import chunk_python_code

logger = logging.getLogger(__name__)

class IncrementalIndexer:
    def __init__(self, vector_store, embedding_model=None):
        """Store a vector store supporting async upsert and delete_by_metadata.

        The optional embedding_model is retained but is not currently used.
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    async def index_file(self, filepath: str, content: str, repo_id: int, commit_sha: str):
        """Upsert Python symbol chunks using placeholder 1,536-element zero vectors.

        Non-.py paths are ignored. Metadata includes repository and commit IDs
        and source locations, but no source content is passed to the store. Chunk
        IDs combine repository, filepath, and symbol; stale symbols are not removed.
        Store errors propagate and may leave earlier chunks already written.
        """
        if not filepath.endswith(".py"):
            logger.info(f"Skipping non-python file: {filepath}")
            return

        chunks = chunk_python_code(content, filepath)

        for chunk in chunks:
            # Here we would call the embedding model
            # embedding = await self.embedding_model.embed(chunk["content"])
            embedding = [0.0] * 1536 # Mock embedding

            metadata = {
                "filepath": chunk["filepath"],
                "symbol_name": chunk["symbol_name"],
                "type": chunk["type"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "commit_sha": commit_sha,
                "repo_id": repo_id
            }

            # Store in vector DB
            await self.vector_store.upsert(
                id=f"{repo_id}_{filepath}_{chunk['symbol_name']}",
                vector=embedding,
                metadata=metadata
            )

    async def remove_file(self, filepath: str, repo_id: int):
        """Remove all chunks associated with a file in the specified repository.

        Vector store deletion errors propagate.
        """
        await self.vector_store.delete_by_metadata(
            repo_id=repo_id,
            filepath=filepath
        )
