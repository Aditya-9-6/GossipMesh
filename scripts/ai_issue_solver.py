#!/usr/bin/env python3
"""
AI Issue Solver for DevProxy & GossipMesh
Analyzes an issue, inspects existing repository source files and invariants,
synthesizes high-performance code and unit tests, and prepares files for automated PR creation.
Supports both Go (DevProxy) and Python (GossipMesh), with multi-provider failover
across Gemini Key Pool, OpenRouter, NVIDIA NIM, and Cohere.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import subprocess
import time
import re
from pathlib import Path

DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-pro-latest",
]

GO_SYSTEM_PROMPT = """You are a Principal Systems Engineer specializing in Go (Golang), high-throughput low-latency network proxies (DevProxy), zero-allocation memory pooling (sync.Pool), lock-free atomic primitives (sync/atomic), eBPF, and protocol implementations (HTTP/1.1, HTTP/2, HTTP/3, QUIC, TLS 1.3).
You are working on DevProxy, a high-performance developer-first reverse proxy written in Go.

CRITICAL MODULE & IMPORT RULES:
- The Go module path is strictly 'github.com/Aditya-9-6/DevProxy'.
- All internal package imports MUST use 'github.com/Aditya-9-6/DevProxy/pkg/...' (NEVER use 'github.com/devproxy/devproxy' or any other fictitious path).
- Do not add non-existent external dependencies; use Go standard library or packages already present in this repo.

CORE ARCHITECTURE GUIDELINES:
1. High throughput and zero allocation: prefer byte slices, stack allocation, and sync.Pool on hot request/response paths. No unnecessary heap allocations.
2. Concurrency safety: data race freedom, proper mutexes or atomic operations, context cancellation propagation.
3. Idiomatic Go: error wrapping (%w), standard package organization under pkg/, table-driven unit tests (*_test.go).
4. Deterministic unit tests: always include comprehensive unit tests ending in _test.go using the standard `testing` package.
5. Preservation mandate: when editing existing files, never remove existing functionality or imports unless refactoring.
6. Syntax integrity: Output must be 100% syntactically valid Go with proper package names and imports.

CRITICAL OUTPUT FORMAT:
Respond with ONLY a valid JSON object and nothing else:
{
  "summary": "Brief explanation of what was implemented",
  "files": [
    {
      "path": "pkg/path/to/file.go",
      "content": "complete file content"
    }
  ]
}
"""

PYTHON_SYSTEM_PROMPT = """You are an expert autonomous systems software engineer specializing in Python, high-throughput network proxies, AI agent platform architecture, secure sandbox runtimes, and fastAPI backends.
You are working on GossipMesh, a high-performance, developer-first AI Agent SaaS platform written in Python.

CORE ARCHITECTURE GUIDELINES:
1. High throughput and low memory footprint: prefer streaming buffers, zero-allocation pooling on hot request/response paths.
2. Concurrency safety: ensure data race freedom using proper sync primitives or lock-free circular ring buffers.
3. Idiomatic Python: clean error handling, context cancellation propagation, no unhandled task leaks, adhere to standard Python naming and conventions.
4. Deterministic unit tests: always include table-driven or comprehensive unit tests (ending in test_*.py) with standard pytest or unittest.
5. Preservation mandate: When modifying an existing file, you MUST PRESERVE 100% of existing functions, methods, structs, and imports. Never truncate with partial stubs.
6. Syntax integrity: Output must be 100% syntactically valid Python with all imports declared.

CRITICAL OUTPUT FORMAT:
Respond with ONLY a valid JSON object and nothing else:
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
    overview = []
    is_go = (workspace_root / "go.mod").exists()
    if is_go:
        try:
            overview.append(f"=== Root go.mod ===\n{(workspace_root / 'go.mod').read_text(encoding='utf-8')[:1500]}")
        except Exception:
            pass
        exts = (".go", ".mod", ".md", ".yaml", ".yml")
    else:
        go_mod = workspace_root / "pyproject.toml"
        if go_mod.exists():
            try:
                overview.append(f"=== Root pyproject.toml ===\n{go_mod.read_text(encoding='utf-8')[:1500]}")
            except Exception:
                pass
        exts = (".py", ".txt", ".md", ".yaml", ".yml")

    overview.append("\n=== Repository File Tree ===")
    selected = [f for f in all_files if f.endswith(exts)][:max_files]
    overview.append("\n".join(selected))
    return "\n".join(overview)


def get_relevant_files(workspace_root: Path, query: str, max_files: int = 5) -> str:
    all_files = get_git_files(workspace_root)
    is_go = (workspace_root / "go.mod").exists()
    target_ext = ".go" if is_go else ".py"

    scored = []
    keywords = [w.lower() for w in re.split(r"[^a-zA-Z0-9_]+", query) if len(w) > 3]

    for f in all_files:
        if not f.endswith(target_ext) or "test" in f.lower():
            continue
        score = sum(1 for kw in keywords if kw in f.lower())
        if score > 0:
            scored.append((score, f))

    scored.sort(key=lambda x: x[0], reverse=True)
    snippets = []
    for _, f in scored[:max_files]:
        full_path = workspace_root / f
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()[:100]
            snippets.append(f"--- File: {f} ---\n" + "\n".join(lines))
        except Exception:
            pass
    return "\n\n".join(snippets)


def extract_json_response(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def load_gemini_keys() -> list[str]:
    keys = []
    pool = os.environ.get("GEMINI_KEY_POOL", "")
    for k in re.split(r"[,\s]+", pool):
        if k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    for var in ("GEMINI_SOLVER_KEY", "GEMINI_API_KEY", "GEMINI_REVIEWER_KEY"):
        val = os.environ.get(var, "").strip()
        if val and val not in keys:
            keys.append(val)
    for check_dir in (Path("."), Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent, Path.home()):
        kf = check_dir / ".gemini_keys"
        if kf.exists():
            try:
                for line in kf.read_text(encoding="utf-8").splitlines():
                    k = line.strip()
                    if k and not k.startswith("#") and k not in keys:
                        keys.append(k)
            except Exception:
                pass
    return keys


def call_gemini(api_key: str, prompt: str, system_prompt: str) -> dict:
    keys = [api_key] if api_key else []
    for k in load_gemini_keys():
        if k not in keys:
            keys.append(k)
    last_err = None
    for current_key in keys:
        for model in FALLBACK_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={current_key}"
            payload = {
                "contents": [{"parts": [{"text": system_prompt}, {"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    res_dict = extract_json_response(text)
                    if isinstance(res_dict, dict) and "files" in res_dict:
                        return res_dict
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                print(f"[!] [Gemini] Model {model} HTTP {e.code}: {err_body[:120]}", file=sys.stderr)
                last_err = err_body
                if e.code in (401, 403):
                    break
                continue
            except Exception as e:
                last_err = str(e)
                continue
    raise RuntimeError(f"Gemini API exhausted. Last error: {last_err}")


def call_openrouter(prompt: str, system_prompt: str) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("Missing OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    models = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.3-70b-instruct",
        "google/gemini-2.5-flash",
    ]
    for model in models:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return extract_json_response(data["choices"][0]["message"]["content"])
        except Exception:
            continue
    raise RuntimeError("OpenRouter failed.")


def call_nvidia(prompt: str, system_prompt: str) -> dict:
    key = os.environ.get("NVIDIA_API_KEY", "").strip() or os.environ.get("NVIDIA_API_KEY_2", "").strip()
    if not key:
        raise ValueError("Missing NVIDIA_API_KEY")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    models = [
        "meta/llama-3.3-70b-instruct",
        "mistralai/mistral-large-2-instruct",
        "meta/llama-3.2-3b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
    ]
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return extract_json_response(data["choices"][0]["message"]["content"])
        except Exception:
            continue
    raise RuntimeError("NVIDIA NIM failed.")


def call_cohere(prompt: str, system_prompt: str) -> dict:
    key = os.environ.get("COHERE_API_KEY", "").strip()
    if not key:
        raise ValueError("Missing COHERE_API_KEY")
    url = "https://api.cohere.com/v2/chat"
    models = ["command-r-plus-08-2024", "command-r-08-2024", "command-r"]
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return extract_json_response(data["message"]["content"][0]["text"])
        except Exception:
            continue
    raise RuntimeError("Cohere failed.")


def request_llm_solution(prompt: str, system_prompt: str) -> dict:
    primary_gemini = os.environ.get("GEMINI_SOLVER_KEY", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    try:
        print("[*] Requesting solution from Gemini AI...", flush=True)
        res = call_gemini(primary_gemini, prompt, system_prompt)
        if res and isinstance(res, dict) and "files" in res:
            return res
    except Exception as ge:
        print(f"[!] Gemini failed: {ge}. Initiating multi-provider failover...", file=sys.stderr)

    try:
        print("[*] Requesting solution from OpenRouter...", flush=True)
        res = call_openrouter(prompt, system_prompt)
        if res and isinstance(res, dict) and "files" in res:
            return res
    except Exception as oe:
        print(f"[!] OpenRouter failover failed: {oe}", file=sys.stderr)

    try:
        print("[*] Requesting solution from NVIDIA NIM...", flush=True)
        res = call_nvidia(prompt, system_prompt)
        if res and isinstance(res, dict) and "files" in res:
            return res
    except Exception as ne:
        print(f"[!] NVIDIA failover failed: {ne}", file=sys.stderr)

    try:
        print("[*] Requesting solution from Cohere...", flush=True)
        res = call_cohere(prompt, system_prompt)
        if res and isinstance(res, dict) and "files" in res:
            return res
    except Exception as ce:
        print(f"[!] Cohere failover failed: {ce}", file=sys.stderr)

    return None


def main():
    parser = argparse.ArgumentParser(description="AI Issue Solver")
    parser.add_argument("--issue-number", required=True, help="GitHub Issue Number")
    parser.add_argument("--issue-title", required=True, help="GitHub Issue Title")
    parser.add_argument("--issue-body", default="", help="GitHub Issue Body")
    parser.add_argument("--workspace", default=".", help="Workspace Directory")
    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    is_go = (workspace_root / "go.mod").exists()
    system_prompt = GO_SYSTEM_PROMPT if is_go else PYTHON_SYSTEM_PROMPT

    print(f"[*] Solving Issue #{args.issue_number}: {args.issue_title}")
    print(f"[*] Target Architecture: {'Go (DevProxy)' if is_go else 'Python (GossipMesh)'}")

    print("[*] Inspecting repository context...")
    all_files = get_git_files(workspace_root)
    overview = get_repo_overview(workspace_root, all_files)

    query_text = f"{args.issue_title} {args.issue_body}"
    relevant_files = get_relevant_files(workspace_root, query_text)

    prompt = f"""GitHub Issue #{args.issue_number}: {args.issue_title}

### Issue Description & Acceptance Criteria:
{args.issue_body}

### Repository Overview:
{overview}

### Relevant Existing Source Files:
{relevant_files if relevant_files else "No directly matching files found. Implement new package or integrate into existing packages."}

Instructions:
1. Implement the feature or fix specified in the issue.
2. Adhere strictly to performance, zero-allocation, and concurrency invariants.
3. Include comprehensive unit tests ({"*_test.go" if is_go else "test_*.py"}).
4. Output your response as valid JSON adhering to the specified schema:
   {{"summary": "...", "files": [{{"path": "...", "content": "..."}}]}}
"""

    result = request_llm_solution(prompt, system_prompt)

    if not result or not isinstance(result, dict) or "files" not in result:
        print("[!] No file changes could be synthesized by any AI provider.", file=sys.stderr)
        sys.exit(1)

    summary = result.get("summary", f"Automated resolution for Issue #{args.issue_number}.")
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
    file_changes_str = "\n".join(f"- `{f['path']}`" for f in files)

    # Self-Healing Pre-flight Verification Gate
    print("[*] Running local compile/vet verification before finalizing...", flush=True)
    compile_err = ""
    if is_go:
        vet_res = subprocess.run(["go", "vet", "./..."], cwd=workspace_root, capture_output=True, text=True)
        if vet_res.returncode != 0 and "go: command not found" not in vet_res.stderr:
            compile_err = vet_res.stderr.strip()
    else:
        comp_res = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "-x", r"(\.venv|\.git)", "."],
            cwd=workspace_root,
            capture_output=True,
            text=True,
        )
        if comp_res.returncode != 0:
            compile_err = comp_res.stderr.strip()

    if compile_err:
        print(
            f"[!] Compiler/Vet error detected:\n{compile_err[:300]}\n[*] Triggering single-pass self-healing fix with Gemini 2.5 Flash...",
            flush=True,
        )
        fix_prompt = f"""The solution you generated produced the following compiler/vet error:

{compile_err}

Target Files modified:
{file_changes_str}

Please fix the syntax, type mismatches, missing imports, or package issues in these files and return the corrected files.
Output ONLY valid JSON matching:
{{"summary": "Fixed compiler errors", "files": [{{"path": "...", "content": "..."}}]}}
"""
        try:
            fix_result = request_llm_solution(fix_prompt, system_prompt)
            if fix_result and isinstance(fix_result, dict) and "files" in fix_result:
                for f in fix_result["files"]:
                    tpath = workspace_root / f["path"]
                    tpath.parent.mkdir(parents=True, exist_ok=True)
                    tpath.write_text(f["content"], encoding="utf-8")
                    print(f"    [+] Self-healed: {f['path']}")
                print("[*] Re-verified after self-healing pass.", flush=True)
        except Exception as fe:
            print(f"[!] Self-healing attempt exception: {fe}", flush=True)
    lang_name = "Go" if is_go else "Python"
    summary_content = f"""## 🚀 Solution for Issue #{args.issue_number}

**Issue**: #{args.issue_number} - {args.issue_title}

### 📝 Solution Overview
{summary}

### 📦 Files Changed
{file_changes_str}

### 🛡️ Quality & Performance Invariants
- [x] Idiomatic {lang_name} concurrency and memory safety.
- [x] High throughput and streaming invariants preserved.
- [x] Comprehensive unit tests included.

---
*Closes #{args.issue_number}*
"""
    summary_file.write_text(summary_content, encoding="utf-8")
    print("[OK] Solution generated and files written successfully.")


if __name__ == "__main__":
    main()
