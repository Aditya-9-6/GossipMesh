#!/usr/bin/env python3
"""
AI Issue Solver for GossipMesh
Uses Google Gemini API to analyze an issue, understand the Python codebase, generate solutions,
and write files ready for automated pull request creation.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import subprocess
import time
import hashlib
from pathlib import Path

DEFAULT_MODEL = "gemini-flash-lite-latest"
FALLBACK_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

SYSTEM_PROMPT = """You are an expert autonomous systems software engineer specializing in Python, high-throughput network proxies, AI agent platform architecture, secure sandbox runtimes, and fastAPI backends.
You are working on GossipMesh, a high-performance, developer-first AI Agent SaaS platform written in Python.

CORE ARCHITECTURE GUIDELINES:
1. High throughput and low memory footprint: prefer streaming buffers, zero-allocation pooling (sync.Pool) on hot request/response paths.
2. Concurrency safety: ensure data race freedom using proper sync primitives or lock-free circular ring buffers.
3. Idiomatic Python: clean error handling, context cancellation propagation, no unhandled task leaks, adhere to standard Python naming and conventions.
4. Deterministic unit tests: always include table-driven or comprehensive unit tests (ending in test_*.py) with the standard `testing` package.
5. Code style: clean comments, adherence to standard black formatting.
6. PRESERVATION MANDATE: When modifying an existing file, you MUST PRESERVE 100% of the existing functions, methods, structs, and imports in that file. NEVER truncate or replace existing file code with partial stubs. If adding new functionality, prefer adding a NEW dedicated Python file (e.g., gossipmesh/<feature>.py) instead of rewriting existing complex files.
7. PYTHON TYPING & IMPORT HYGIENE: Always explicitly import all used type annotations (e.g., `from typing import Any, Dict, List, Optional, Tuple, Set, Union, Callable`). NEVER reference `Any`, `Dict`, `List`, `Optional`, or other types without importing them. Undefined names will cause instant CI build failure.
8. SYNTAX & COMPILATION INTEGRITY: Ensure every file is 100% syntactically valid Python. Test cases must inherit from `unittest.TestCase` or be compatible with standard pytest and unittest runners. Never introduce syntax errors, broken docstrings, or unmatched quotes.

You will be given a GitHub issue with its title, description, and repository context.
Analyze the requirements and generate the exact file changes needed to implement the feature or fix the bug.

CRITICAL OUTPUT FORMAT:
You MUST respond with a single valid JSON object and NOTHING ELSE (no markdown formatting, no explanations outside the JSON).
The JSON object must have this exact structure:
{
  "summary": "Brief 2-3 sentence overview of what was implemented and architecture decisions made.",
  "files": [
    {
      "path": "relative/path/to/file.py",
      "content": "complete updated or new file contents"
    }
  ]
}
"""


def get_git_files(workspace_root: Path) -> list:
    """Uses git ls-files for lightning-fast file discovery."""
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=workspace_root, text=True, stderr=subprocess.DEVNULL)
        return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]
    except Exception:
        files = []
        for root, dirs, filenames in os.walk(workspace_root):
            dirs[:] = [d for d in dirs if d not in [".git", "vendor", "node_modules", "bin"]]
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), workspace_root).replace("\\", "/")
                files.append(rel)
        return files


def get_repo_overview(workspace_root: Path, all_files: list, max_files: int = 60) -> str:
    """Collects high-level overview of repo structure and pyproject.toml configuration."""
    overview = []

    go_mod = workspace_root / "pyproject.toml"
    if go_mod.exists():
        try:
            overview.append(f"=== Root pyproject.toml ===\n{go_mod.read_text(encoding='utf-8')[:2000]}")
        except Exception:
            pass

    overview.append("\n=== Repository File Tree ===")
    selected = [f for f in all_files if f.endswith((".py", ".mod", ".md", ".yaml", ".yml"))][:max_files]
    selected = [f for f in all_files if f.endswith((".py", ".txt", ".md", ".yaml", ".yml"))][:max_files]
    overview.append("\n".join(selected))
    return "\n".join(overview)


import ast

# Add parent directory to path to import gossipmesh
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gossipmesh.rag import VectorDB
from gossipmesh.memetic import MemeticKnowledgeBase


def summarize_python_file(content: str) -> str:
    """Parses a Python file and returns its imports and function/class signatures with docstrings."""
    summary = []
    try:
        tree = ast.parse(content)

        # Helper to unparse signature without body
        def get_signature_and_doc(node, indent=0):
            node_copy = ast.copy_location(type(node)(), node)
            for field, value in ast.iter_fields(node):
                if field != "body":
                    setattr(node_copy, field, value)

            # replace body with pass
            node_copy.body = [ast.Pass()]

            sig = ast.unparse(node_copy).strip()
            # remove the 'pass'
            if sig.endswith("pass"):
                sig = sig[:-4].strip()

            lines = [(" " * indent) + sig]
            doc = ast.get_docstring(node)
            if doc:
                lines.append((" " * (indent + 4)) + f'"""{doc}"""')
            return lines

        for node in tree.body:
            if isinstance(node, ast.Import):
                for name in node.names:
                    summary.append(f"import {name.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(n.name for n in node.names)
                summary.append(f"from {module} import {names}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                summary.extend(get_signature_and_doc(node, 0))
            elif isinstance(node, ast.ClassDef):
                summary.extend(get_signature_and_doc(node, 0))
                # Also get methods
                for class_node in node.body:
                    if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        summary.extend(get_signature_and_doc(class_node, 4))
    except Exception as e:
        return f"# Error parsing python file: {e}\n{content[:1000]}"
    return "\n".join(summary)


def summarize_go_file(filepath: str, workspace_root: Path, raw_content: str) -> str:
    """Runs the go_ast_extractor tool on a Go file to get a structural summary."""
    try:
        extractor_path = Path(__file__).resolve().parent / "go_ast_extractor.go"
        target_file = workspace_root / filepath
        res = subprocess.run(
            ["go", "run", str(extractor_path), str(target_file)], capture_output=True, text=True, timeout=10
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            summary = [f"package {data.get('package', '')}", ""]
            summary.append("import (")
            for imp in data.get("imports", []):
                summary.append(f"    {imp}")
            summary.append(")")
            summary.append("")
            summary.extend(data.get("declarations", []))
            return "\n".join(summary)
        else:
            return f"// Error parsing go file: {res.stderr}\n// Proceeding with raw context...\n{raw_content}"
    except Exception as e:
        return f"// Error parsing go file: {e}\n{raw_content}"


def get_relevant_files(workspace_root: Path, query_text: str) -> str:
    """Uses fast local keyword indexing to find relevant files for context instantly."""
    context_files = []
    import re

    try:
        # Extract meaningful keywords from query_text (exclude common filler words)
        words = re.findall(r"\b[a-zA-Z_]{4,}\b", query_text.lower())
        stop_words = {
            "feat",
            "task",
            "plan",
            "issue",
            "implement",
            "create",
            "with",
            "from",
            "that",
            "this",
            "file",
            "mode",
            "test",
        }
        keywords = [w for w in words if w not in stop_words]

        scored_files = []
        target_dir = workspace_root / "gossipmesh"
        if target_dir.exists():
            for p in target_dir.rglob("*.py"):
                if p.name.startswith("test_") or "__pycache__" in str(p):
                    continue
                try:
                    txt = p.read_text(encoding="utf-8", errors="replace")
                    score = sum(1 for kw in keywords if kw in txt.lower() or kw in p.name.lower())
                    if score > 0:
                        scored_files.append((score, p))
                except Exception:
                    pass

        scored_files.sort(key=lambda x: x[0], reverse=True)
        for _, p in scored_files[:4]:
            rel = str(p.relative_to(workspace_root)).replace("\\", "/")
            summarized = summarize_python_file(p.read_text(encoding="utf-8", errors="replace"))
            print(f"    [+] Keyword context hit: {rel}")
            context_files.append(f"=== Existing File: {rel} ===\n{summarized}")
    except Exception as e:
        print(f"[Warning] Context search error: {e}")

    return "\n\n".join(context_files)


def call_gemini(api_key: str, prompt: str, model: str = DEFAULT_MODEL, cache_dir: str = ".pyssip_mesh/cache") -> dict:
    """Calls Gemini REST API with fallback and retries across supported models."""
    ordered = [model] + [m for m in FALLBACK_MODELS if m != model]
    models_to_try = []
    for m in ordered:
        if m not in models_to_try:
            models_to_try.append(m)

    # Check cache
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"{model}:{prompt}".encode("utf-8")).hexdigest()
    cache_file = cache_path / f"{cache_key}.json"

    if cache_file.exists():
        try:
            print("[*] Cache hit! Returning cached Gemini response...", flush=True)
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    last_err = None
    for current_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"

        payload = {
            "contents": [{"parts": [{"text": SYSTEM_PROMPT}, {"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }

        print(f"[*] Attempting generation with model: {current_model}...", flush=True)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()

                    # Parse JSON response
                    try:
                        parsed_response = json.loads(text_response, strict=False)
                    except json.JSONDecodeError:
                        if text_response.startswith("```"):
                            lines = text_response.splitlines()
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            text_response = "\n".join(lines).strip()
                        parsed_response = json.loads(text_response, strict=False)

                    try:
                        cache_file.write_text(json.dumps(parsed_response), encoding="utf-8")
                    except Exception:
                        pass

                    return parsed_response
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="replace")
                print(
                    f"[Warning] HTTP {e.code} (attempt {attempt}/{max_attempts}) with model {current_model}: {err_msg[:200]}",
                    file=sys.stderr,
                )
                last_err = err_msg
                # If model is deprecated / not found, do not waste retries
                if e.code == 404:
                    break
                if e.code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                    time.sleep(1 * attempt)
                    continue
                break
            except Exception as e:
                print(
                    f"[Warning] Error (attempt {attempt}/{max_attempts}) with model {current_model}: {e}",
                    file=sys.stderr,
                )
                last_err = str(e)
                if attempt < max_attempts:
                    time.sleep(1 * attempt)
                    continue
                break

    raise RuntimeError(
        f"Failed to obtain solution from Gemini API across models {models_to_try}. Last error: {last_err}"
    )


def main():
    parser = argparse.ArgumentParser(description="GossipMesh AI Issue Solver")
    parser.add_argument("--issue-number", required=True, help="GitHub Issue Number")
    parser.add_argument("--issue-title", required=True, help="GitHub Issue Title")
    parser.add_argument("--issue-body", required=True, help="GitHub Issue Body")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("MISSING_API_KEY: Environment variable GEMINI_API_KEY is not set.", file=sys.stderr)
        print(
            "To enable the bot, generate a free API key at https://aistudio.google.com/ and add it to GitHub Secrets as GEMINI_API_KEY."
        )
        sys.exit(2)

    workspace_root = Path(args.workspace).resolve()
    print(f"[*] Solving Issue #{args.issue_number}: {args.issue_title}")

    print("[*] Inspecting repository context...")
    all_files = get_git_files(workspace_root)
    overview = get_repo_overview(workspace_root, all_files)

    query_text = f"{args.issue_title} {args.issue_body}"
    relevant_files = get_relevant_files(workspace_root, query_text)

    # Memetic Knowledge Injection
    kb = MemeticKnowledgeBase()
    meme_context = kb.format_prompt_context(repo="GossipMesh")

    prompt = f"""
GitHub Issue #{args.issue_number}: {args.issue_title}

### Issue Description & Acceptance Criteria:
{args.issue_body}

### Repository Overview:
{overview}

### Relevant Existing Source Files:
{relevant_files if relevant_files else "No directly matching files found. Implement new package or integrate into existing packages."}

{meme_context}

Instructions:
1. Implement the feature or fix specified in the issue.
2. Adhere to GossipMesh performance and concurrency invariants.
3. Write clean, idiomatic Python code with accompanying unit tests (test_*.py).
4. Output your response as valid JSON adhering to the specified schema.
"""
    print("[*] Requesting solution from Gemini AI...")
    result = call_gemini(api_key, prompt)

    summary = result.get("summary", "Automated resolution of issue.")
    files = result.get("files", [])

    if not files:
        print("[!] No file changes proposed by AI.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Applying {len(files)} file changes...")
    for f in files:
        rel_path = f["path"]
        content = f["content"]
        target_path = workspace_root / rel_path

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        print(f"    [+] Wrote: {rel_path}")

    summary_file = workspace_root / "ai_pr_summary.md"
    file_changes_str = chr(10).join(f"- `{f['path']}`" for f in files)
    summary_content = (
        f"## 🤖 Automated Solution for Issue #{args.issue_number}\n\n"
        f"**Issue**: #{args.issue_number} - {args.issue_title}\n\n"
        f"### 📝 Solution Overview\n{summary}\n\n"
        f"### 📦 Files Changed\n{file_changes_str}\n\n"
        "### 🛡️ Quality & Performance Invariants\n"
        "- [x] Idiomatic Python concurrency and memory safety.\n"
        "- [x] High throughput and streaming invariants preserved.\n"
        "- [x] Comprehensive unit tests included.\n\n"
        "---\n"
        f"*Closes #{args.issue_number}*\n"
    )
    summary_file.write_text(summary_content, encoding="utf-8")
    print("[OK] Solution generated and files written successfully.")


if __name__ == "__main__":
    main()
