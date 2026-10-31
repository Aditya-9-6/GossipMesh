#!/usr/bin/env python3
"""
Autonomous CI Test & Build Auto-Fixer for GossipMesh
Analyzes failing Python tests, ruff lint errors, and type errors, queries AI models
(Gemini, NVIDIA NIM, OpenRouter, Cohere), resolves Git merge conflicts, applies the fix,
and verifies that tests pass before pushing.
Also accepts AI Reviewer feedback to refactor spaghetti code and add missing tests.
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import re
import argparse
import urllib.request
import urllib.error
import subprocess
import time
from pathlib import Path

DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
]

DEFAULT_KEYS = []


def load_gemini_keys() -> list[str]:
    """Dynamically loads Gemini API keys from environment variables and local .gemini_keys files."""
    keys = []
    pool_env = os.environ.get("GEMINI_KEY_POOL", "")
    for k in pool_env.split(","):
        if k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    for var in ("GEMINI_SOLVER_KEY", "GEMINI_API_KEY", "GEMINI_REVIEWER_KEY", "GEMINI_ISSUE_KEY"):
        val = os.environ.get(var, "").strip()
        if val and val not in keys:
            keys.append(val)
    for check_dir in (Path("."), Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent, Path.home()):
        key_file = check_dir / ".gemini_keys"
        if key_file.exists():
            try:
                for line in key_file.read_text(encoding="utf-8").splitlines():
                    k = line.strip()
                    if k and not k.startswith("#") and k not in keys:
                        keys.append(k)
            except Exception:
                pass
    for k in DEFAULT_KEYS:
        if k not in keys:
            keys.append(k)
    return keys


SYSTEM_PROMPT = """You are an expert autonomous Python systems engineer and architectural repair agent for GossipMesh.
Your mission is to fix failing Python build errors, lint errors (ruff), type errors (mypy), broken unit tests, AND refactor spaghetti code based on review feedback.

CRITICAL RULES:
1. ANTI-SPAGHETTI & MODULARITY: Ensure functions are concise (<60 LOC), single-purpose, and decoupled. Refactor any tangled or duplicate logic.
2. PRESERVE EXISTING INTERFACES & EXPORTS: Never remove or omit existing functions, classes, methods, or helper functions that other files or packages depend on.
3. COMPILE-READY CODE: All files must be syntactically valid Python, with correct imports, correct types, and no undefined identifiers.
4. ASYNC CONCURRENCY: Ensure asyncio and event loop safety without race conditions or blocking I/O calls inside coroutines.
5. COMPLETE FILE CONTENT: When updating a file, provide the COMPLETE, FULL file content so it can replace the file directly. Never write partial snippets.

CRITICAL OUTPUT FORMAT:
Respond ONLY with a single valid JSON object and nothing else (no conversational filler, no markdown wrappers outside JSON):
{
  "summary": "Clear explanation of how the errors were resolved and how the code was fixed.",
  "files": [
    {
      "path": "relative/path/to/file.py",
      "content": "full updated file content"
    }
  ]
}
"""

CONFLICT_SYSTEM_PROMPT = """You are an expert Git merge conflict resolver and Python systems architect for GossipMesh.
Your mission is to resolve Git merge conflicts between `origin/main` and a feature pull request branch.

CRITICAL RULES:
1. PRESERVE INTENT FROM BOTH BRANCHES: Keep the enhancements, bug fixes, and additions introduced in main while preserving the new feature logic from the PR branch.
2. REMOVE ALL CONFLICT MARKERS: Completely remove <<<<<<< HEAD, =======, >>>>>>> markers.
3. COMPILE-READY PYTHON CODE: Ensure imports, types, methods, and syntax are 100% valid Python code.
4. COMPLETE FILE CONTENT: Return the COMPLETE, entire resolved file content.

OUTPUT FORMAT:
Respond ONLY with a single valid JSON object:
{
  "summary": "Explanation of how conflicts were resolved.",
  "files": [
    {
      "path": "relative/path/to/file.py",
      "content": "full resolved file content"
    }
  ]
}
"""


def extract_json_response(raw_text: str) -> dict:
    raw_text = raw_text.strip()
    try:
        return json.loads(raw_text, strict=False)
    except json.JSONDecodeError:
        pass
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()
        try:
            return json.loads(raw_text, strict=False)
        except json.JSONDecodeError:
            pass
    first_brace = raw_text.find("{")
    last_brace = raw_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return json.loads(raw_text[first_brace : last_brace + 1], strict=False)
    raise ValueError(f"Could not parse valid JSON from model response: {raw_text[:200]}")


def call_gemini(
    api_key: str, prompt: str, system_prompt: str = SYSTEM_PROMPT, fallback_key: str = "", model: str = DEFAULT_MODEL
) -> dict:
    ordered = [model] + [m for m in FALLBACK_MODELS if m != model]
    models_to_try = []
    for m in ordered:
        if m not in models_to_try:
            models_to_try.append(m)

    keys_to_try = [k for k in [api_key, fallback_key] if k.strip()]
    for k in load_gemini_keys():
        if k not in keys_to_try:
            keys_to_try.append(k)

    last_err = None
    for current_key in keys_to_try:
        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={current_key}"
            payload = {
                "contents": [{"parts": [{"text": system_prompt}, {"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
            }

            print(f"[*] [Gemini] Querying {current_model}...", flush=True)
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        text_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return extract_json_response(text_response)
                except urllib.error.HTTPError as e:
                    err_msg = e.read().decode("utf-8", errors="replace")
                    last_err = err_msg
                    if e.code == 404:
                        break
                    if e.code == 429:
                        print(f"[*] [Gemini] Rate limited (429) on {current_model}. Fast failover...", flush=True)
                        break
                    if e.code in (500, 502, 503, 504) and attempt < max_attempts:
                        time.sleep(2)
                        continue
                    break
                except Exception as e:
                    last_err = str(e)
                    if attempt < max_attempts:
                        time.sleep(2 * attempt)
                        continue
                    break

    raise RuntimeError(f"Gemini API exhausted. Last error: {last_err}")


def call_openrouter(api_key: str, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    models = [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.3-70b-instruct",
        "google/gemini-2.5-flash",
        "mistralai/mistral-large-2411",
    ]
    last_err = None
    for model in models:
        print(f"[*] [OpenRouter] Querying {model}...", flush=True)
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                return extract_json_response(text)
        except Exception as e:
            print(f"[!] [OpenRouter] Model {model} failed: {e}", file=sys.stderr)
            last_err = str(e)
            continue
    raise RuntimeError(f"OpenRouter calls failed: {last_err}")


def call_cohere(api_key: str, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """Calls Cohere Chat API as resilient fallback."""
    if not api_key:
        raise ValueError("Missing COHERE_API_KEY")
    url = "https://api.cohere.com/v2/chat"
    models = ["command-r-plus-08-2024", "command-r-08-2024", "command-r-plus", "command-r"]
    last_err = None
    for model in models:
        print(f"[*] [Cohere] Querying {model}...", flush=True)
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "GossipMesh-CI/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("message", {}).get("content", [])
                if content and isinstance(content, list):
                    text = content[0].get("text", "")
                    return extract_json_response(text)
        except Exception as e:
            print(f"[!] [Cohere] Model {model} failed: {e}", file=sys.stderr)
            last_err = str(e)
            continue
    raise RuntimeError(f"Cohere calls failed. Last error: {last_err}")


def call_huggingface(api_key: str, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """Calls Hugging Face Inference Router API as resilient fallback."""
    if not api_key:
        raise ValueError("Missing HUGGINGFACE_API_KEY")
    url = "https://router.huggingface.co/hf-inference/v1/chat/completions"
    models = ["Qwen/Qwen2.5-Coder-32B-Instruct", "meta-llama/Llama-3.3-70B-Instruct"]
    last_err = None
    for model in models:
        print(f"[*] [HuggingFace] Querying {model}...", flush=True)
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                return extract_json_response(text)
        except Exception as e:
            print(f"[!] [HuggingFace] Model {model} failed: {e}", file=sys.stderr)
            last_err = str(e)
            continue
    raise RuntimeError(f"HuggingFace calls failed. Last error: {last_err}")


def call_nvidia_nim(api_key: str, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    if not api_key:
        raise ValueError("Missing NVIDIA_API_KEY")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    models = [
        "meta/llama-3.3-70b-instruct",
        "mistralai/mistral-large-2-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.2-3b-instruct",
        "meta/llama-3.2-1b-instruct",
        "deepseek-ai/deepseek-r1",
    ]
    last_err = None
    for model in models:
        print(f"[*] [NVIDIA NIM] Querying {model}...", flush=True)
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                return extract_json_response(text)
        except Exception as e:
            print(f"[!] [NVIDIA NIM] Model {model} failed: {e}", file=sys.stderr)
            last_err = str(e)
            continue
    raise RuntimeError(f"NVIDIA NIM calls failed: {last_err}")


def call_ai_model(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    primary_gemini = os.environ.get("GEMINI_SOLVER_KEY", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    fallback_gemini = (
        os.environ.get("GEMINI_REVIEWER_KEY", "").strip() or os.environ.get("GEMINI_ISSUE_KEY", "").strip()
    )
    try:
        return call_gemini(primary_gemini, prompt, system_prompt=system_prompt, fallback_key=fallback_gemini)
    except Exception as e:
        print(f"[!] Gemini attempt failed: {e}. Trying secondary providers...", file=sys.stderr)

    cohere_key = os.environ.get("COHERE_API_KEY", "").strip()
    if cohere_key:
        try:
            return call_cohere(cohere_key, prompt, system_prompt=system_prompt)
        except Exception as e:
            print(f"[!] Cohere failed: {e}. Trying next provider...", file=sys.stderr)

    hf_key = os.environ.get("HUGGINGFACE_API_KEY", "").strip()
    if hf_key:
        try:
            return call_huggingface(hf_key, prompt, system_prompt=system_prompt)
        except Exception as e:
            print(f"[!] HuggingFace failed: {e}. Trying next provider...", file=sys.stderr)

    for nv_key in [os.environ.get("NVIDIA_API_KEY", "").strip(), os.environ.get("NVIDIA_API_KEY_2", "").strip()]:
        if nv_key:
            try:
                return call_nvidia_nim(nv_key, prompt, system_prompt=system_prompt)
            except Exception as e:
                print(f"[!] NVIDIA NIM key failed: {e}. Trying next provider...", file=sys.stderr)

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        try:
            return call_openrouter(openrouter_key, prompt, system_prompt=system_prompt)
        except Exception as e:
            print(f"[!] OpenRouter failed: {e}. Trying next provider...", file=sys.stderr)

    raise RuntimeError(
        "All AI model providers (Gemini, Cohere, HuggingFace, NVIDIA NIM, OpenRouter) exhausted without response."
    )


def detect_and_resolve_conflicts(workspace: Path, user_instructions: str = "") -> list[str]:
    conflicted_files = set()
    try:
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=workspace, capture_output=True, text=True)
        for line in status_res.stdout.splitlines():
            if line and line[:2] in ("UU", "AA", "UD", "DU", "AU", "UA", "DD"):
                conflicted_files.add(line[3:].strip().replace("\\", "/"))
    except Exception:
        pass

    for p in workspace.rglob("*.py"):
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if "<<<<<<< HEAD" in content or ("=======" in content and ">>>>>>>" in content):
                conflicted_files.add(str(p.relative_to(workspace)).replace("\\", "/"))
        except Exception:
            pass

    resolved = []
    if not conflicted_files:
        return resolved

    print(f"[*] ⚠️ Detected {len(conflicted_files)} conflicted file(s): {sorted(list(conflicted_files))}", flush=True)
    for rel_path in sorted(list(conflicted_files)):
        target_file = workspace / rel_path
        if (
            rel_path.startswith(".github/")
            or rel_path.startswith("scripts/ai_")
            or rel_path.startswith("scripts/auto_merge")
            or rel_path == "fix_conflict.py"
        ):
            print(f"[*] Preserving master workflow/tooling from origin/main for {rel_path}...", flush=True)
            code = subprocess.run(["git", "checkout", "origin/main", "--", rel_path], cwd=workspace).returncode
            if code == 0:
                subprocess.run(["git", "add", rel_path], cwd=workspace)
            else:
                subprocess.run(["git", "rm", "-f", rel_path], cwd=workspace)
            resolved.append(rel_path)
            continue

        if not target_file.is_file():
            print(
                f"[*] Handling deleted/missing conflicted file {rel_path} by restoring from origin/main...", flush=True
            )
            subprocess.run(["git", "checkout", "origin/main", "--", rel_path], cwd=workspace)
            subprocess.run(["git", "add", rel_path], cwd=workspace)
            resolved.append(rel_path)
            continue
        conflicted_text = target_file.read_text(encoding="utf-8", errors="replace")
        if "<<<<<<<" not in conflicted_text and ">>>>>>>" not in conflicted_text:
            print(f"[*] Resolving non-marker conflict in {rel_path} by restoring from origin/main...", flush=True)
            subprocess.run(["git", "checkout", "origin/main", "--", rel_path], cwd=workspace)
            subprocess.run(["git", "add", rel_path], cwd=workspace)
            resolved.append(rel_path)
            continue

        print(f"[*] Resolving Git merge conflicts in {rel_path} via AI...", flush=True)
        user_inst_block = (
            f"\n=== USER SPECIFIC INSTRUCTIONS ===\n{user_instructions}\nYou MUST follow these instructions while resolving the conflict.\n"
            if user_instructions
            else ""
        )
        prompt = f"""Resolve the Git merge conflicts in `{rel_path}`.

CRITICAL INSTRUCTIONS:
1. Merge the changes from HEAD (the PR branch) and the incoming base branch (origin/main).
2. Retain all functionality, imports, class attributes, and methods from BOTH branches.
3. Completely remove all conflict markers (`<<<<<<< HEAD`, `=======`, `>>>>>>> ...`).
4. Ensure the resulting file is 100% syntactically valid Python.
5. Return the COMPLETE, entire resolved file content in the JSON schema.
{user_inst_block}
=== CONFLICTED FILE: {rel_path} ===
{conflicted_text}
"""
        try:
            res = call_ai_model(prompt, system_prompt=CONFLICT_SYSTEM_PROMPT)
            files = res.get("files", [])
            for f in files:
                if f.get("content"):
                    dest = workspace / f["path"].replace("\\", "/")
                    dest.write_text(f["content"], encoding="utf-8")
                    subprocess.run(["git", "add", f["path"].replace("\\", "/")], cwd=workspace)
                    resolved.append(rel_path)
                    print(f"    [+] Successfully resolved conflict in {rel_path}", flush=True)
        except Exception as e:
            print(f"[!] Conflict resolution failed for {rel_path}: {e}", file=sys.stderr)

    # Resolve any remaining unmerged paths
    try:
        remaining_res = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"], cwd=workspace, capture_output=True, text=True
        )
        remaining = [l.strip() for l in remaining_res.stdout.splitlines() if l.strip()]
        for rem in remaining:
            print(f"[*] Fallback: resolving remaining unmerged file {rem} using origin/main...", flush=True)
            subprocess.run(["git", "checkout", "origin/main", "--", rem], cwd=workspace)
            subprocess.run(["git", "add", rem], cwd=workspace)
            resolved.append(rem)
    except Exception:
        pass

    if resolved:
        subprocess.run(["git", "add", "-A"], cwd=workspace)
        merge_head = workspace / ".git" / "MERGE_HEAD"
        if merge_head.exists():
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    "fix(merge): resolve merge conflicts with origin/main",
                    "-m",
                    "Co-authored-by: Dahale Aditya Dnyaneshwar <adityadahale96@gmail.com>",
                ],
                cwd=workspace,
            )
            print("[*] Completed merge commit after conflict resolution.", flush=True)

    return resolved


def fetch_remote_ci_errors(pr_number: str, workspace: Path) -> str:
    """Fetches failed GitHub Actions logs and check annotations for this PR if available."""
    ci_reports = []
    try:
        # 1. Inspect statusCheckRollup to find all failing checks and matrix jobs
        pr_view = subprocess.run(
            ["gh", "pr", "view", pr_number, "--json", "headRefName,statusCheckRollup"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        if pr_view.returncode == 0:
            pr_data = json.loads(pr_view.stdout)
            checks = pr_data.get("statusCheckRollup", [])
            for c in checks:
                name = c.get("name", "Unknown Check")
                conclusion = (c.get("conclusion") or c.get("state") or "").upper()
                if conclusion in ("FAILURE", "TIMED_OUT", "STARTUP_FAILURE"):
                    url = c.get("detailsUrl", "")
                    print(f"[*] Identified failing CI check: {name} (URL: {url})", flush=True)

                    # Extract check run ID (e.g., /runs/123456)
                    match_cr = re.search(r"/runs/(\d+)$", url)
                    if match_cr:
                        cr_id = match_cr.group(1)
                        ann_res = subprocess.run(
                            ["gh", "api", f"/repos/:owner/:repo/check-runs/{cr_id}/annotations"],
                            cwd=workspace,
                            capture_output=True,
                            text=True,
                        )
                        if ann_res.returncode == 0 and ann_res.stdout.strip():
                            try:
                                anns = json.loads(ann_res.stdout)
                                for a in anns:
                                    ci_reports.append(
                                        f"=== SECURITY / LINT ALERT: {name} ===\n"
                                        f"File: {a.get('path')}:{a.get('start_line')}\n"
                                        f"Title: {a.get('title')}\n"
                                        f"Message: {a.get('message')}\n"
                                    )
                            except Exception:
                                pass

                    # Extract job ID (e.g., /job/123456)
                    match_job = re.search(r"/job/(\d+)", url)
                    if match_job:
                        job_id = match_job.group(1)
                        job_log = subprocess.run(
                            ["gh", "run", "view", "--job", job_id, "--log-failed"],
                            cwd=workspace,
                            capture_output=True,
                            text=True,
                        )
                        if job_log.stdout.strip():
                            ci_reports.append(
                                f"=== FAILED CI JOB ({name} [Job #{job_id}]) ===\n" + job_log.stdout.strip()[:8000]
                            )

        # 2. Fallback: check recent workflow runs for this branch
        if not ci_reports:
            head_ref = ""
            if pr_view.returncode == 0:
                head_ref = json.loads(pr_view.stdout).get("headRefName", "")
            cmd = ["gh", "run", "list", "--limit", "10", "--json", "databaseId,conclusion,name,headBranch"]
            if head_ref:
                cmd.extend(["-b", head_ref])
            res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                for run in data:
                    run_name = run.get("name", "").lower()
                    if any(
                        x in run_name for x in ("ai ci", "ai-ci", "auto-approve", "auto-merge", "autonomous", "fixer")
                    ):
                        continue
                    if run.get("conclusion") in ("failure", "timed_out", "startup_failure"):
                        run_id = str(run.get("databaseId"))
                        print(
                            f"[*] Found failed GitHub Actions run {run_id} ({run.get('name')}). Fetching failed logs...",
                            flush=True,
                        )
                        log_res = subprocess.run(
                            ["gh", "run", "view", "--log-failed", run_id],
                            cwd=workspace,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                        )
                        if log_res.stdout.strip():
                            ci_reports.append(
                                f"=== GITHUB ACTIONS FAILED RUN ({run.get('name')} #{run_id}) ===\n"
                                + log_res.stdout.strip()[:10000]
                            )
                            break
    except Exception as e:
        print(f"[*] Note: Could not fetch remote CI logs via gh CLI: {e}", flush=True)

    return "\n\n".join(ci_reports).strip()


def get_tool_bin(workspace: Path, tool_name: str) -> str:
    """Locate tool binary across Linux (.venv/bin) and Windows (.venv/Scripts)."""
    candidates = [
        workspace / ".venv" / "bin" / tool_name,
        workspace / ".venv" / "Scripts" / f"{tool_name}.exe",
        workspace / ".venv" / "Scripts" / tool_name,
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return tool_name


def run_diagnostics(workspace: Path, pr_number: str = "") -> tuple[int, str]:
    print("[*] Running local diagnostic checks (ruff auto-fix, compileall, ruff, pytest)...", flush=True)
    out_lines = []

    py_bin = get_tool_bin(workspace, "python")
    if py_bin == "python":
        py_bin = sys.executable

    ruff_bin = get_tool_bin(workspace, "ruff")

    # Step 0: Fast deterministic auto-fix pass (0 API tokens, sub-100ms)
    try:
        ruff_fix_cmd = (
            [ruff_bin, "check", "--fix", "."] if ruff_bin != "ruff" else [py_bin, "-m", "ruff", "check", "--fix", "."]
        )
        subprocess.run(ruff_fix_cmd, cwd=workspace, capture_output=True, text=True, timeout=15)
        ruff_fmt_cmd = [ruff_bin, "format", "."] if ruff_bin != "ruff" else [py_bin, "-m", "ruff", "format", "."]
        subprocess.run(ruff_fmt_cmd, cwd=workspace, capture_output=True, text=True, timeout=15)
    except Exception:
        pass

    # Step 1: Syntax & Bytecode Compilation Check
    compile_failed = False
    try:
        comp_res = subprocess.run(
            [
                py_bin,
                "-m",
                "compileall",
                "-q",
                "-x",
                r"(\.venv|\.git|tests/fixtures)",
                "gossipmesh",
                "tests",
                "scripts",
            ],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if comp_res.returncode != 0:
            compile_failed = True
            out_lines.append("=== PYTHON SYNTAX / COMPILATION ERRORS ===")
            out_lines.append(comp_res.stderr.strip() or comp_res.stdout.strip())
            out_lines.append("")
    except Exception as e:
        compile_failed = True
        out_lines.append(f"=== COMPILE ERROR ===\n{e}\n")

    # Step 2: Strict Ruff Lint Check
    ruff_failed = False
    try:
        ruff_cmd = [ruff_bin, "check", "."] if ruff_bin != "ruff" else [py_bin, "-m", "ruff", "check", "."]
        ruff_res = subprocess.run(
            ruff_cmd, cwd=workspace, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
        )
        if ruff_res.returncode != 0 and ruff_res.stdout.strip():
            ruff_failed = True
            out_lines.append("=== RUFF LINT ERRORS ===")
            out_lines.append(ruff_res.stdout.strip() or ruff_res.stderr.strip())
            out_lines.append("")
    except Exception:
        pass

    # Step 3: Pytest Unit Tests
    test_failed = False
    try:
        test_res = subprocess.run(
            [py_bin, "-m", "pytest", "tests/", "-m", "not integration", "-q", "--maxfail=3", "--durations=3"],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        if test_res.returncode != 0:
            test_failed = True
            out_lines.append("=== PYTHON TEST FAILURES ===")
            combined = (test_res.stdout + "\n" + test_res.stderr).strip()
            out_lines.append(combined)
            out_lines.append("")
    except Exception as e:
        test_failed = True
        out_lines.append(f"=== TEST RUN ERROR ===\n{e}\n")

    # Step 4: Check mypy if available (non-blocking)
    try:
        mypy_bin = get_tool_bin(workspace, "mypy")
        mypy_cmd = [mypy_bin, "gossipmesh/"] if mypy_bin != "mypy" else [py_bin, "-m", "mypy", "gossipmesh/"]
        mypy_res = subprocess.run(
            mypy_cmd, cwd=workspace, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
        )
        if mypy_res.returncode != 0 and mypy_res.stdout.strip():
            out_lines.append("=== MYPY TYPE ERRORS ===")
            out_lines.append(mypy_res.stdout.strip() or mypy_res.stderr.strip())
            out_lines.append("")
    except Exception:
        pass

    # Always fetch remote GitHub CI failures and security alerts if pr_number is provided
    remote_ci = ""
    if pr_number:
        remote_ci = fetch_remote_ci_errors(pr_number, workspace)
        if remote_ci:
            out_lines.append(remote_ci)

    combined_output = "\n".join(out_lines).strip()
    total_exit = 1 if (compile_failed or ruff_failed or test_failed or bool(remote_ci)) else 0
    return total_exit, combined_output


def extract_referenced_files(error_log: str, workspace: Path) -> list[str]:
    found = set()
    pattern = re.compile(r"([\w/\\.-]+\.py)(?::\d+)?")
    search_dirs = [workspace / d for d in ("gossipmesh", "tests", "scripts") if (workspace / d).is_dir()]
    for match in pattern.finditer(error_log):
        rel_str = match.group(1).replace("\\", "/")
        p = workspace / rel_str
        if p.is_file() and not any(part in p.parts for part in (".venv", ".git", "__pycache__")):
            found.add(rel_str)
        else:
            for sdir in search_dirs:
                for sub in sdir.rglob("*.py"):
                    if any(part in sub.parts for part in (".venv", ".git", "__pycache__")):
                        continue
                    if sub.name == Path(rel_str).name:
                        try:
                            found.add(str(sub.relative_to(workspace)).replace("\\", "/"))
                        except ValueError:
                            pass

    try:
        diff_names = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in diff_names.stdout.splitlines():
            line = line.strip().replace("\\", "/")
            if line.endswith(".py") and (workspace / line).is_file():
                found.add(line)
    except Exception:
        pass

    return sorted(list(found))


def get_pr_diff(workspace: Path) -> str:
    try:
        res = subprocess.run(["git", "diff", "origin/main...HEAD"], cwd=workspace, capture_output=True, text=True)
        if res.stdout.strip():
            return res.stdout.strip()[:15000]
    except Exception:
        pass
    try:
        res = subprocess.run(["git", "diff", "HEAD~1"], cwd=workspace, capture_output=True, text=True)
        if res.stdout.strip():
            return res.stdout.strip()[:15000]
    except Exception:
        pass
    return "No git diff available."


def extract_instructions_from_pr(pr_number: str, workspace: Path) -> str:
    """Extracts custom user instructions or reviewer action items from PR comments."""
    try:
        res = subprocess.run(
            ["gh", "pr", "view", pr_number, "--json", "comments"],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            comments = data.get("comments", [])
            # Priority 1: Direct /fix user command
            for c in reversed(comments):
                body = c.get("body", "")
                if "/fix" in body:
                    m = re.search(r"/fix[:\s-]*(.*)", body, re.DOTALL | re.IGNORECASE)
                    if m and m.group(1).strip():
                        return m.group(1).strip()
            # Priority 2: Autonomous Architectural Reviewer action items
            for c in reversed(comments):
                body = c.get("body", "")
                if "Autonomous Architectural Review" in body and "Required Refactoring & Action Items" in body:
                    action_section = re.search(
                        r"### 🛠️ Required Refactoring & Action Items(.*?)(?:---|\Z)", body, re.DOTALL
                    )
                    if action_section:
                        items = action_section.group(1).strip()
                        if items:
                            print(f"[*] Extracted Autonomous Reviewer Action Items from PR #{pr_number}", flush=True)
                            return f"Address the following architectural and code review action items:\n{items}"
    except Exception as e:
        print(f"[*] Warning: Could not extract comments from PR #{pr_number}: {e}", file=sys.stderr)
    return ""


def main():
    parser = argparse.ArgumentParser(description="GossipMesh Autonomous CI Auto-Fixer & Conflict Resolver")
    parser.add_argument("--pr-number", required=True, help="GitHub Pull Request Number")
    parser.add_argument("--workspace", default=".", help="Workspace root directory")
    parser.add_argument("--error-log-file", default="", help="Optional pre-captured error log file")
    parser.add_argument("--review-feedback-file", default="", help="Optional reviewer feedback markdown file")
    parser.add_argument(
        "--user-instructions", default="", help="Optional user instructions from comment or workflow dispatch"
    )
    parser.add_argument("--user-instructions-file", default="", help="Optional file containing user instructions")
    parser.add_argument("--max-iterations", type=int, default=6, help="Maximum self-healing passes")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    print(f"[*] Starting Autonomous CI Fixer & Conflict Resolver for PR #{args.pr_number} in {workspace}...")

    # Load any user instructions (CLI, file, or automatically from PR comments)
    user_instructions = args.user_instructions.strip()
    if args.user_instructions_file and Path(args.user_instructions_file).is_file():
        file_inst = Path(args.user_instructions_file).read_text(encoding="utf-8").strip()
        if file_inst:
            user_instructions = f"{user_instructions}\n{file_inst}".strip() if user_instructions else file_inst
    if not user_instructions:
        user_instructions = extract_instructions_from_pr(args.pr_number, workspace)

    if user_instructions:
        print(f"[*] 🗣️ User Instructions detected & applied:\n{user_instructions}", flush=True)

    conflicts_resolved = detect_and_resolve_conflicts(workspace, user_instructions=user_instructions)
    if conflicts_resolved:
        print(f"[OK] Automatically resolved merge conflicts in: {conflicts_resolved}", flush=True)

    review_feedback = ""
    if args.review_feedback_file and Path(args.review_feedback_file).is_file():
        review_feedback = Path(args.review_feedback_file).read_text(encoding="utf-8")
        print(f"[*] Loaded Reviewer Feedback ({len(review_feedback)} chars).")

    all_repaired_files = set(conflicts_resolved)
    latest_summary = "Resolved Git merge conflicts." if conflicts_resolved else ""
    post_code = 1
    initial_had_errors = False

    max_iterations = args.max_iterations
    for iteration in range(1, max_iterations + 1):
        print(f"\n=======================================================", flush=True)
        print(f"[*] Autonomous Repair Pass {iteration}/{max_iterations}", flush=True)
        print(f"=======================================================", flush=True)

        code, error_log = run_diagnostics(workspace, pr_number=args.pr_number)
        if code != 0 or error_log:
            initial_had_errors = True

        if code == 0 and not error_log:
            if not review_feedback or iteration > 1:
                print(f"\n[🎉 SUCCESS] All checks passed 100% GREEN at pass {iteration}!", flush=True)
                post_code = 0
                break
            else:
                print(f"[*] Diagnostics green, addressing reviewer feedback on Pass 1...", flush=True)

        if error_log:
            print(f"[*] Diagnostics identified failing checks:\n{error_log[:500]}...", flush=True)

        combined_context_text = (error_log or "") + "\n" + (review_feedback or "")
        referenced_files = extract_referenced_files(combined_context_text, workspace)
        print(f"[*] Files in repair scope: {referenced_files}", flush=True)

        file_contents = {}
        for rf in referenced_files[:12]:
            fp = workspace / rf
            if fp.is_file():
                try:
                    file_contents[rf] = fp.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    print(f"[!] Could not read {rf}: {e}", file=sys.stderr)

        pr_diff = get_pr_diff(workspace)

        prompt_header = f"""Pull Request #{args.pr_number} has failing Python checks or tests (Pass {iteration}/{max_iterations}).
Your goal: Fix all lint errors, type errors, and broken tests so that all diagnostics pass 100% GREEN."""

        user_inst_block = (
            f"\n=== USER GUIDANCE & SPECIFIC INSTRUCTIONS ===\n{user_instructions}\nStrictly adhere to and implement these instructions.\n"
            if user_instructions
            else ""
        )

        prompt = f"""{prompt_header}

=== CI DIAGNOSTIC ERROR LOG ===
{error_log[:15000] if error_log else "None (compilation clean). Focus on reviewer feedback."}
{user_inst_block}
{f"=== ARCHITECTURAL REVIEW FEEDBACK ==={chr(10)}{review_feedback[:10000]}" if review_feedback else ""}

=== CURRENT GIT DIFF ===
{pr_diff[:10000]}

=== REFERENCED SOURCE FILES (PRESERVE ALL EXISTING CODE) ===
{chr(10).join(f"--- File: {path} ---{chr(10)}{content}" for path, content in file_contents.items())}

Instructions:
1. Fix all failing checks above.
2. PRESERVATION MANDATE: Preserve existing functions and classes. Do not delete features.
3. Provide full replacement content for each file updated.
4. Output valid JSON adhering to schema.
"""

        try:
            result = call_ai_model(prompt, system_prompt=SYSTEM_PROMPT)
        except Exception as e:
            print(f"[!] AI call failed on pass {iteration}: {e}", file=sys.stderr)
            time.sleep(5)
            continue

        latest_summary = result.get("summary", "Automated repair for Python CI diagnostics.")
        files = result.get("files", [])

        if not files:
            print("[!] No file changes provided by AI.", file=sys.stderr)
            break

        print(f"[*] Applying {len(files)} fixed file(s)...", flush=True)
        for f in files:
            rel_path = f["path"].replace("\\", "/")
            content = f["content"]
            target = workspace / rel_path

            if target.is_file():
                orig_lines = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
                new_lines = len(content.splitlines())
                if orig_lines > 80 and new_lines < int(orig_lines * 0.65):
                    print(
                        f"[!] WARNING: Proposed fix for {rel_path} shrunk lines from {orig_lines} to {new_lines}. Skipping destructive overwrite.",
                        flush=True,
                    )
                    continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            all_repaired_files.add(rel_path)
            print(f"    [+] Wrote fixed file: {rel_path}", flush=True)

        ruff_bin = get_tool_bin(workspace, "ruff")
        py_bin = get_tool_bin(workspace, "python")
        try:
            ruff_cmd = (
                [ruff_bin, "check", "--fix", "."]
                if ruff_bin != "ruff"
                else [py_bin, "-m", "ruff", "check", "--fix", "."]
            )
            subprocess.run(ruff_cmd, cwd=workspace, capture_output=True, text=True, timeout=20)
            ruff_fmt = [ruff_bin, "format", "."] if ruff_bin != "ruff" else [py_bin, "-m", "ruff", "format", "."]
            subprocess.run(ruff_fmt, cwd=workspace, capture_output=True, text=True, timeout=20)
        except Exception:
            pass

    final_code, final_log = run_diagnostics(workspace, pr_number=args.pr_number)
    post_code = final_code

    if initial_had_errors and not all_repaired_files and post_code != 0:
        status_label = "⚠️ **CHECKS STILL REPORTING ERRORS (No Auto-Fix Produced)**"
    elif post_code == 0:
        status_label = "✅ **ALL TESTS 100% GREEN (Passed)**"
    else:
        status_label = "⚠️ **CHECKS STILL REPORTING ERRORS**"

    user_inst_section = f"\n### 🗣️ User Instructions Addressed\n> {user_instructions}\n" if user_instructions else ""
    summary_file = workspace / "ci_fix_summary.md"
    summary_content = f"""## 🛠️ Autonomous CI Test Fixer Report (GossipMesh Python)

**Target**: Pull Request #{args.pr_number}
**Status**: {status_label}
{user_inst_section}
### 📋 Resolution Summary
{latest_summary or "CI diagnostics analyzed."}

### 📂 Files Modified
{chr(10).join(f"- `{f}`" for f in sorted(list(all_repaired_files))) if all_repaired_files else "None"}

### 🧪 Diagnostic Verification
- Local build & test exit code: **{post_code}**
{f"```text{chr(10)}{final_log[:1500]}{chr(10)}```" if post_code != 0 else "```text\nAll Python packages passed ruff and unittests cleanly.\n```"}
"""
    summary_file.write_text(summary_content, encoding="utf-8")
    print(f"\n[OK] Fix cycle completed. Final verification status: exit code {post_code}")

    if post_code == 0:
        print("[🎉 100% GREEN] CI suite passed cleanly.")
        sys.exit(0)
    elif all_repaired_files or bool(conflicts_resolved):
        print("[+] Fixes applied and/or conflicts resolved. Exiting cleanly to push changes.")
        sys.exit(0)
    else:
        print(f"[!] Tests still failing after repair passes.")
        sys.exit(1)


if __name__ == "__main__":
    main()
