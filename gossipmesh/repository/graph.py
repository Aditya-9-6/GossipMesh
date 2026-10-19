import networkx as nx
import ast
from typing import Dict, Any


class ArchitectureGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_files(self, files: Dict[str, str]):
        """
        Builds a dependency graph from a dictionary of filepath -> content.
        Very basic implementation looking for 'import' and 'from ... import'.
        """
        for filepath, content in files.items():
            if not filepath.endswith(".py"):
                continue

            self.graph.add_node(filepath, type="file")

            try:
                tree = ast.parse(content, filename=filepath)
                for node in tree.body:
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            # Simplified representation of an import
                            target = f"{name.name.replace('.', '/')}.py"
                            self.graph.add_edge(filepath, target, type="imports")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            target = f"{node.module.replace('.', '/')}.py"
                            self.graph.add_edge(filepath, target, type="imports")
            except SyntaxError:
                pass

    def get_dependencies(self, filepath: str) -> list:
        if filepath in self.graph:
            return list(self.graph.successors(filepath))
        return []

    def get_dependents(self, filepath: str) -> list:
        if filepath in self.graph:
            return list(self.graph.predecessors(filepath))
        return []
