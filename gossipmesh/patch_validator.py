import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import re
import ast
import difflib

from pathlib import Path

class PatchValidator:
    def __init__(self, authorized_paths, forbidden_files, max_file_count, max_file_size, max_diff_size):
        self.authorized_paths = authorized_paths
        self.forbidden_files = forbidden_files
        self.max_file_count = max_file_count
        self.max_file_size = max_file_size
        self.max_diff_size = max_diff_size

    def validate_patch(self, patch):
        # Validate relative paths
        for file_path in patch.keys():
            if not file_path.startswith("."):
                raise ValueError(f"Absolute path detected: {file_path}")

        # Validate workspace containment
        workspace_root = str(Path(__file__).resolve().parent.parent)
        for file_path in patch.keys():
            if not file_path.startswith(workspace_root):
                raise ValueError(f"File outside workspace: {file_path}")

        # Validate symlink escapes
        for file_path in patch.keys():
            if "/../" in file_path:
                raise ValueError(f"Symlink escape detected: {file_path}")

        # Validate forbidden files
        for file_path in patch.keys():
            if any(file_path.endswith(f) for f in self.forbidden_files):
                raise ValueError(f"Forbidden file: {file_path}")

        # Validate file count
        if len(patch) > self.max_file_count:
            raise ValueError(f"File count exceeded: {len(patch)}")

        # Validate file size
        for file_path, content in patch.items():
            if os.path.getsize(file_path) > self.max_file_size:
                raise ValueError(f"File size exceeded: {os.path.getsize(file_path)}")

        # Validate total diff size
        total_diff_size = sum(len(content) for content in patch.values())
        if total_diff_size > self.max_diff_size:
            raise ValueError(f"Total diff size exceeded: {total_diff_size}")

        # Validate UTF-8 encoding
        for file_path, content in patch.items():
            try:
                content.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError(f"Non-UTF-8 content in {file_path}")

        # Validate Python syntax
        for file_path, content in patch.items():
            if file_path.endswith(".py"):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    raise ValueError(f"Python syntax error in {file_path}: {e}")

        # Validate JSON schema (if applicable)
        for file_path, content in patch.items():
            if file_path.endswith(".json"):
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"JSON decoding error in {file_path}: {e}")

        # Validate authorized paths
        for file_path in patch.keys():
            if not any(file_path.startswith(path) for path in self.authorized_paths):
                raise ValueError(f"Unauthorized file access: {file_path}")


# Example usage
if __name__ == "__main__":
    validator = PatchValidator(
        authorized_paths=["gossipmesh/",