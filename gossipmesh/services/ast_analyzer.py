import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any

import git
import tree_sitter_rust
import tree_sitter_cpp
from tree_sitter import Language, Parser

logger = logging.getLogger(__name__)


class AstAnalyzer:
    def __init__(self):
        self.rust_lang = Language(tree_sitter_rust.language())
        self.cpp_lang = Language(tree_sitter_cpp.language())

    def _parse_diff(self, diff_text: str) -> Dict[str, List[int]]:
        """Parses a diff and returns a dict mapping filename to list of added/modified line numbers."""
        modified_files = {}
        current_file = None
        current_line = 0

        for line in diff_text.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]
                modified_files[current_file] = []
            elif line.startswith("@@"):
                match = re.search(r"\+([0-9]+)", line)
                if match and current_file:
                    current_line = int(match.group(1))
            elif line.startswith("+") and not line.startswith("+++") and current_file:
                modified_files[current_file].append(current_line)
                current_line += 1
            elif line.startswith(" ") and current_file:
                current_line += 1

        return modified_files

    def analyze_pr(self, repo_url: str, diff_text: str) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Cloning {repo_url} into {temp_dir}")
            repo = git.Repo.clone_from(repo_url, temp_dir)

            # Write diff_text to a patch file and apply it
            patch_path = Path(temp_dir) / "pr.patch"
            patch_path.write_text(diff_text)
            try:
                # Use standard git apply instead of git python for simpler patch application
                repo.git.apply("pr.patch")
                logger.info("Successfully applied PR diff")
            except git.exc.GitCommandError as e:
                logger.error(f"Failed to apply patch: {e}")
                # We can choose to proceed or return empty. We proceed, but the ast
                # might be out of sync. For now just log.

            return self._analyze_directory(Path(temp_dir), diff_text)

    def _find_rust_function_declarations(self, node) -> List[Tuple[str, int, int]]:
        funcs = []
        if node.type == "function_item":
            for child in node.children:
                if child.type == "identifier":
                    # start_point is (row, column). 0-indexed, so row+1 is line number
                    funcs.append((child.text.decode("utf8"), node.start_point[0] + 1, node.end_point[0] + 1))
        for child in node.children:
            funcs.extend(self._find_rust_function_declarations(child))
        return funcs

    def _find_rust_function_calls(self, node) -> List[Tuple[str, int]]:
        calls = []
        if node.type == "call_expression":
            for child in node.children:
                if child.type == "identifier":
                    calls.append((child.text.decode("utf8"), node.start_point[0] + 1))
                elif child.type == "field_expression":
                    for c in child.children:
                        if c.type == "field_identifier":
                            calls.append((c.text.decode("utf8"), node.start_point[0] + 1))
                elif child.type == "scoped_identifier":
                    for c in child.children:
                        if c.type == "identifier":
                            calls.append((c.text.decode("utf8"), node.start_point[0] + 1))
        for child in node.children:
            calls.extend(self._find_rust_function_calls(child))
        return calls

    def _find_cpp_function_declarations(self, node) -> List[Tuple[str, int, int]]:
        funcs = []
        if node.type == "function_definition":
            for child in node.children:
                if child.type == "function_declarator":
                    for c in child.children:
                        if c.type == "identifier":
                            funcs.append((c.text.decode("utf8"), node.start_point[0] + 1, node.end_point[0] + 1))
                        elif c.type == "field_identifier":
                            funcs.append((c.text.decode("utf8"), node.start_point[0] + 1, node.end_point[0] + 1))
                        elif c.type == "scoped_identifier":
                            for sc in c.children:
                                if sc.type == "identifier":
                                    funcs.append(
                                        (sc.text.decode("utf8"), node.start_point[0] + 1, node.end_point[0] + 1)
                                    )
        for child in node.children:
            funcs.extend(self._find_cpp_function_declarations(child))
        return funcs

    def _find_cpp_function_calls(self, node) -> List[Tuple[str, int]]:
        calls = []
        if node.type == "call_expression":
            for child in node.children:
                if child.type == "identifier":
                    calls.append((child.text.decode("utf8"), node.start_point[0] + 1))
                elif child.type == "field_expression":
                    for c in child.children:
                        if c.type == "field_identifier":
                            calls.append((c.text.decode("utf8"), node.start_point[0] + 1))
                elif child.type == "scoped_identifier":
                    for c in child.children:
                        if c.type == "identifier":
                            calls.append((c.text.decode("utf8"), node.start_point[0] + 1))
        for child in node.children:
            calls.extend(self._find_cpp_function_calls(child))
        return calls

    def _analyze_directory(self, repo_path: Path, diff_text: str) -> str:
        modified_files = self._parse_diff(diff_text)

        modified_functions = []  # List of dicts with file, func_name, changed_lines

        all_rust_files = list(repo_path.rglob("*.rs"))
        all_cpp_files = (
            list(repo_path.rglob("*.cpp"))
            + list(repo_path.rglob("*.cc"))
            + list(repo_path.rglob("*.hpp"))
            + list(repo_path.rglob("*.h"))
        )

        rust_parser = Parser(self.rust_lang)
        cpp_parser = Parser(self.cpp_lang)

        # Step 1: Find modified functions in changed files
        for rel_file_path, changed_lines in modified_files.items():
            if not changed_lines:
                continue

            file_path = repo_path / rel_file_path
            if not file_path.exists():
                continue

            code = file_path.read_bytes()

            if rel_file_path.endswith(".rs"):
                tree = rust_parser.parse(code)
                decls = self._find_rust_function_declarations(tree.root_node)
            elif any(rel_file_path.endswith(ext) for ext in [".cpp", ".cc", ".hpp", ".h"]):
                tree = cpp_parser.parse(code)
                decls = self._find_cpp_function_declarations(tree.root_node)
            else:
                continue

            for func_name, start_line, end_line in decls:
                # Check if any changed lines fall within this function
                matching_lines = [line for line in changed_lines if start_line <= line <= end_line]
                if matching_lines:
                    modified_functions.append(
                        {"file": rel_file_path, "name": func_name, "changed_lines": matching_lines}
                    )

        # Step 2: Find all downstream dependencies (function calls) in the whole repo
        dependencies: Dict[str, List[Dict[str, Any]]] = {}

        for func_info in modified_functions:
            func_name = func_info["name"]
            if func_name not in dependencies:
                dependencies[func_name] = []

        # Parse all Rust files for calls
        for file_path in all_rust_files:
            rel_path = file_path.relative_to(repo_path).as_posix()
            try:
                code = file_path.read_bytes()
                tree = rust_parser.parse(code)
                calls = self._find_rust_function_calls(tree.root_node)

                for called_func, line_num in calls:
                    if called_func in dependencies:
                        dependencies[called_func].append({"file": rel_path, "line": line_num})
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")

        # Parse all C++ files for calls
        for file_path in all_cpp_files:
            rel_path = file_path.relative_to(repo_path).as_posix()
            try:
                code = file_path.read_bytes()
                tree = cpp_parser.parse(code)
                calls = self._find_cpp_function_calls(tree.root_node)

                for called_func, line_num in calls:
                    if called_func in dependencies:
                        dependencies[called_func].append({"file": rel_path, "line": line_num})
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")

        # Format the output JSON report
        report = []
        for func_info in modified_functions:
            report.append(
                {
                    "modified_file": func_info["file"],
                    "modified_function": func_info["name"],
                    "changed_lines": func_info["changed_lines"],
                    "downstream_dependencies": dependencies.get(func_info["name"], []),
                }
            )

        return json.dumps(report, indent=2)
