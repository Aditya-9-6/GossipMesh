from typing import List, Dict, Any

class HybridRetriever:
    def __init__(self, vector_store, architecture_graph):
        """Store a vector store with async search and a graph with get_dependencies."""
        self.vector_store = vector_store
        self.graph = architecture_graph

    async def search(self, query: str, repo_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return repository matches expanded with immediate dependency placeholders.

        The query is currently unused; search uses a 1,536-element zero vector.
        Pass top_k to the vector store, deduplicate results by filepath, and
        insert dependencies after each retained match. Dependency entries contain
        placeholder content and 80% of the originating score (zero if absent).
        For nonnegative top_k, return at most twice that many entries.
        Store and graph errors, and missing result metadata keys, propagate.
        """
        # 1. Semantic Search (Vector)
        # query_embedding = await self.embedding_model.embed(query)
        query_embedding = [0.0] * 1536

        vector_results = await self.vector_store.search(
            vector=query_embedding,
            filter={"repo_id": repo_id},
            top_k=top_k
        )

        # 2. Graph Expansion
        expanded_results = []
        seen_files = set()

        for res in vector_results:
            filepath = res["metadata"]["filepath"]
            if filepath not in seen_files:
                expanded_results.append(res)
                seen_files.add(filepath)

                # Fetch immediate dependencies from graph
                deps = self.graph.get_dependencies(filepath)
                for dep in deps:
                    if dep not in seen_files:
                        # We would ideally fetch the content of 'dep' here
                        expanded_results.append({
                            "metadata": {"filepath": dep, "type": "dependency_expansion"},
                            "content": f"# Expanded dependency {dep}",
                            "score": res.get("score", 0) * 0.8 # Decay score for expanded items
                        })
                        seen_files.add(dep)

        return expanded_results[:top_k * 2]
