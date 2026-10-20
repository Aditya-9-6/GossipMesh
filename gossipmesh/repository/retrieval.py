from typing import List, Dict, Any


class HybridRetriever:
    def __init__(self, vector_store, architecture_graph):
        self.vector_store = vector_store
        self.graph = architecture_graph

    def search(self, query: str, repo_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs a hybrid search combining vector similarity and graph relationships.
        """
        # 1. Semantic Search (Vector)
        # query_embedding = self.embedding_model.embed(query)
        query_embedding = [0.0] * 1536

        vector_results = self.vector_store.search(vector=query_embedding, filter={"repo_id": repo_id}, top_k=top_k)

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
                        expanded_results.append(
                            {
                                "metadata": {"filepath": dep, "type": "dependency_expansion"},
                                "content": f"# Expanded dependency {dep}",
                                "score": res.get("score", 0) * 0.8,  # Decay score for expanded items
                            }
                        )
                        seen_files.add(dep)

        return expanded_results[: top_k * 2]
