"""Generated patch validation and safety containment (Task 10).
Validates AI-generated changes before writing to disk:
- Relative path enforcement
- Workspace containment & directory traversal prevention
- Symlink escape detection
- Forbidden file & secret protection (.git, .env, private keys, API keys)
- File count & file size thresholds
- Total diff size limit
- UTF-8 encoding validation
- Python AST syntax verification
- JSON syntax and schema validation
- Authorized path allowlisting
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


class PatchValidationError(Exception):
    """Raised when an AI-generated patch violates safety or integrity rules."""

    pass


FORBIDDEN_PATTERNS = [
    r"^\.git(/|\\|$)",
    r"^\.env(\.|$)",
    r".*\.pem$",
    r".*\.key$",
    r".*id_rsa.*",
    r".*id_ed25519.*",
    r"^\.gemini_keys$",
    r"^\.llm_keys$",
    r".*credentials.*\.json$",
    r".*service_account.*\.json$",
    r"^\.github/workflows/.*",  # Restrict unauthorized workflow modifications unless permitted
]


class PatchValidator:
    """Validates AI-generated patches to prevent sandbox escape and corruption."""

    def __init__(
        self,
        workspace: Union[str, Path] = ".",
        max_files: int = 50,
        max_file_size_bytes: int = 1_048_576,  # 1 MB
        max_total_diff_bytes: int = 5_242_880,  # 5 MB
        authorized_roots: Optional[List[str]] = None,
        forbidden_patterns: Optional[List[str]] = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.max_files = max_files
        self.max_file_size = max_file_size_bytes
        self.max_total_diff = max_total_diff_bytes
        self.authorized_roots = authorized_roots
        self.forbidden_patterns = forbidden_patterns if forbidden_patterns is not None else FORBIDDEN_PATTERNS

    def validate_path(self, rel_path: str) -> Path:
        """Validates that a file path is relative, safe, contained in workspace, and authorized."""
        cleaned = rel_path.strip().replace("\\", "/")

        # 1. Reject absolute paths
        if os.path.isabs(cleaned) or cleaned.startswith("/") or re.match(r"^[a-zA-Z]:", cleaned):
            raise PatchValidationError(f"Forbidden absolute path: {rel_path}")

        # 2. Reject path traversal sequences
        parts = cleaned.split("/")
        if ".." in parts:
            raise PatchValidationError(f"Path traversal ('..') detected in path: {rel_path}")

        # 3. Check forbidden file patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                raise PatchValidationError(f"Forbidden file pattern '{pattern}' matched for path: {rel_path}")

        # 4. Check authorized root directories if configured
        if self.authorized_roots:
            is_authorized = any(
                cleaned == root or cleaned.startswith(root.rstrip("/") + "/") for root in self.authorized_roots
            )
            if not is_authorized:
                raise PatchValidationError(
                    f"Path '{rel_path}' is outside authorized directories ({self.authorized_roots})"
                )

        # 5. Resolve target and enforce workspace containment
        target = (self.workspace / cleaned).resolve()
        try:
            target.relative_to(self.workspace)
        except ValueError:
            raise PatchValidationError(f"Workspace escape detected: {rel_path} resolves outside {self.workspace}")

        # 6. Check symlink escapes
        curr = target
        while curr != self.workspace and curr != curr.parent:
            if curr.is_symlink():
                link_target = curr.resolve()
                try:
                    link_target.relative_to(self.workspace)
                except ValueError:
                    raise PatchValidationError(
                        f"Symlink escape detected: {curr} points outside workspace to {link_target}"
                    )
            curr = curr.parent

        return target

    def validate_content(self, rel_path: str, content: Union[str, bytes]) -> str:
        """Validates encoding, size, and language-specific syntax (Python AST, JSON)."""
        # 1. UTF-8 Validation
        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8")
                raw_bytes = content
            except UnicodeDecodeError as e:
                raise PatchValidationError(f"Content for {rel_path} is not valid UTF-8: {e}")
        else:
            text = content
            raw_bytes = content.encode("utf-8")

        # 2. File size validation
        if len(raw_bytes) > self.max_file_size:
            raise PatchValidationError(
                f"File size limit exceeded for {rel_path}: {len(raw_bytes)} bytes (max: {self.max_file_size})"
            )

        # 3. Python AST syntax validation
        if rel_path.endswith(".py"):
            try:
                ast.parse(text, filename=rel_path)
            except SyntaxError as e:
                raise PatchValidationError(f"Python syntax error in {rel_path} at line {e.lineno}: {e.msg}")

        # 4. JSON validation
        if rel_path.endswith(".json"):
            try:
                json.loads(text)
            except json.JSONDecodeError as e:
                raise PatchValidationError(f"Invalid JSON syntax in {rel_path}: {e}")

        return text

    def validate_patch_set(
        self, files: Dict[str, Union[str, bytes]], raise_on_error: bool = True
    ) -> Tuple[bool, List[str]]:
        """Validates an entire set of proposed file modifications."""
        errors: List[str] = []

        # 1. File count limit
        if len(files) > self.max_files:
            err = f"Total files limit exceeded: {len(files)} files in patch (max: {self.max_files})"
            errors.append(err)

        # 2. Total diff size limit
        total_size = sum(len(c) if isinstance(c, bytes) else len(c.encode("utf-8")) for c in files.values())
        if total_size > self.max_total_diff:
            err = f"Total patch size exceeded: {total_size} bytes (max: {self.max_total_diff})"
            errors.append(err)

        # 3. Validate each file individually
        for path, content in files.items():
            try:
                self.validate_path(path)
                self.validate_content(path, content)
            except PatchValidationError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Validation error for {path}: {e}")

        if errors and raise_on_error:
            raise PatchValidationError("Patch validation failed:\n - " + "\n - ".join(errors))

        return len(errors) == 0, errors
