import ast
import os
import unittest
from pathlib import Path


class TestArchitecture(unittest.TestCase):
    def test_domain_models_dependencies(self):
        """
        Enforce that domain models do not depend on outer layers.
        """
        models_dir = Path("gossipmesh/models")
        forbidden_prefixes = (
            "gossipmesh.api",
            "gossipmesh.services",
            "gossipmesh.jobs",
            "gossipmesh.integrations",
            "gossipmesh.workflows",
        )

        for root, _, files in os.walk(models_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = Path(root) / file
                    with open(filepath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=str(filepath))

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                for prefix in forbidden_prefixes:
                                    self.assertFalse(
                                        alias.name.startswith(prefix),
                                        f"Architectural violation in {filepath}: imported {alias.name}",
                                    )
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                for prefix in forbidden_prefixes:
                                    self.assertFalse(
                                        node.module.startswith(prefix),
                                        f"Architectural violation in {filepath}: imported from {node.module}",
                                    )

if __name__ == "__main__":
    unittest.main()
