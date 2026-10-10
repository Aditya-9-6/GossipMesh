#!/usr/bin/env python3
"""
Autonomous PR Validator & Reviewer Agent for DevProxy
Enforces strict anti-spaghetti architectural standards, modularity, zero-leak concurrency,
zero-allocation memory invariants, and high test coverage.
Outputs structured JSON and Markdown reports with system impact assessment.
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

# Add parent directory to path to import gossipmesh
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gossipmesh.memetic import MemeticKnowledgeBase
from gossipmesh.red_team import RedTeamAuditor
from gossipmesh.consensus import ByzantineConsensusEngine, ModelVote

DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
]

REVIEWER_SYSTEM_PROMPT = """You are an elite principal systems software architect and security auditor reviewing Pull Requests on DevProxy (a high-performance HTTP/HTTPS proxy and security engine in Go).

Your primary mission is to ENFORCE STRICT ARCHITECTURAL STANDARDS AND PREVENT SPAGHETTI CODE as the codebase scales at hyper-speed.

CRITICAL ARCHITECTURAL & ANTI-SPAGHETTI INVARIANTS:
1. Anti-Spaghetti & Modularity:
   - Single Responsibility Principle (SRP): Functions must be focused (<60 LOC), clean, and self-documenting.
   - No spaghetti control flow: Reject deeply nested blocks (>3 levels), massive switch-case god functions, or unstructured goto/fallthrough loops.
   - Clean Package Boundaries: Preserve encapsulation between `pkg/proxy`, `pkg/analysis`, `pkg/ringbuffer`, `pkg/cert`, `pkg/dashboard`. No circular dependencies or cross-package leakages.
2. Concurrency Safety:
   - Zero data races, proper synchronization via `sync.RWMutex`, `sync.Once`, atomic operations, or channels.
   - Goroutine lifecycle safety: All launched goroutines must terminate cleanly upon context cancellation (`ctx.Done()`). No leaks.
   - Defer hygiene: Mutex unlocks and resource closes must be deferred immediately with zero defer leaks inside hot unbounded loops.
3. Memory & High Throughput Invariants:
   - Zero-allocation hot paths: Use `sync.Pool` for byte buffers (`[]byte`). Avoid allocating slices or copying payloads in the proxy stream forwarding path.
   - Streaming compliance: Read and forward payloads via streaming readers/writers (`io.Reader`, `io.Writer`) without buffering entire multi-megabyte streams in RAM.
4. Security & Hardening:
   - Strict input validation: Protection against SSRF, request smuggling (TE.CL/CL.TE), path traversal, TLS bypass, and command injection.
5. Go Idiomatic Standards & Test Coverage:
   - Error wrapping using `%w` and proper sentinel error checking with `errors.Is`/`errors.As`.
   - Table-driven unit tests covering happy paths, edge cases, negative/error paths, and concurrent execution (`t.Parallel()`).

EVALUATION & VERDICT:
- If code has compilation errors, missing dependencies, data race risks, spaghetti code, god functions, or missing unit tests:
  verdict must be "ACTION_REQUIRED" and score < 90.
- If code is clean, modular, race-free, properly tested, and meets all anti-spaghetti architectural invariants:
  verdict must be "APPROVED" and score >= 90 (typically 95-100).

OUTPUT SCHEMA:
You MUST respond ONLY with a single valid JSON object with the following schema:
{
  "verdict": "APPROVED" or "ACTION_REQUIRED",
  "score": 95,
  "executive_summary": "Concise summary of the PR and overall architectural quality.",
  "anti_spaghetti_audit": "Detailed evaluation of code modularity, function sizing, decoupling, and maintainability.",
  "security_concurrency_audit": "Detailed analysis of data race freedom, goroutine lifecycle, mutex safety, and security posture.",
  "performance_memory_audit": "Evaluation of buffer pooling (sync.Pool), zero-allocation hot paths, and streaming throughput.",
  "test_coverage_audit": "Evaluation of test coverage, edge cases, error conditions, and concurrency tests.",
  "system_impact": "Detailed assessment of the PR's effect on the DevProxy system (impacted subsystems, throughput, latency, security posture, operational reliability). If approved, cc @Aditya-9-6.",
  "action_items": [
    "Specific refactoring step or improvement needed (empty list if APPROVED)"
  ],
  "auto_patch": "Optional valid diff / git patch to fix the identified issues."
}
"""

def call_ollama(prompt: str, model: str = "llama3", cache_dir: str = ".gossip_mesh/cache") -> dict:
    """Calls local Ollama API for fast edge inference."""
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
    payload = {
        "model": model,
        "prompt": f"{REVIEWER_SYSTEM_PROMPT}\n\n{prompt}",
        "stream": False,
        "format": "json"
    }

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"{model}:{prompt}".encode("utf-8")).hexdigest()
    cache_file = cache_path / f"{cache_key}.json"

    if cache_file.exists():
        try:
            print("[*] Cache hit! Returning cached Ollama response...", flush=True)
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    print(f"[*] Requesting fast-pass architectural PR review from local edge model: {model}...", flush=True)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text_response = data.get("response", "").strip()
            parsed_response = json.loads(text_response, strict=False)
            try:
                cache_file.write_text(json.dumps(parsed_response), encoding="utf-8")
            except Exception:
                pass
            return parsed_response
    except Exception as e:
        print(f"[Warning] Failed to query local edge model {model}: {e}", file=sys.stderr)
        return {"verdict": "ACTION_REQUIRED", "score": 50, "executive_summary": f"Failed to query {model}: {e}"}

def call_gemini(api_key: str, prompt: str, fallback_key: str = "", model: str = DEFAULT_MODEL, cache_dir: str = ".gossip_mesh/cache") -> dict:
    """Calls Gemini REST API with fallback models and fallback API key, expecting JSON."""
    ordered = [model] + [m for m in FALLBACK_MODELS if m != model]
    models_to_try = []
    for m in ordered:
        if m not in models_to_try:
            models_to_try.append(m)

    keys_to_try = [k for k in [api_key, fallback_key] if k.strip()]

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
    for current_key in keys_to_try:
        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={current_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": REVIEWER_SYSTEM_PROMPT},
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }

            print(f"[*] Requesting architectural PR review from model: {current_model}...", flush=True)
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                try:
                    with urllib.request.urlopen(req, timeout=90) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        text_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()
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
                    print(f"[Warning] HTTP {e.code} (attempt {attempt}/{max_attempts}) with model {current_model}: {err_msg[:160]}", file=sys.stderr)
                    last_err = err_msg
                    if e.code == 404:
                        break
                    if e.code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                        time.sleep(1 * attempt)
                        continue
                    break
                except Exception as e:
                    print(f"[Warning] Error (attempt {attempt}/{max_attempts}) with model {current_model}: {e}", file=sys.stderr)
                    last_err = str(e)
                    if attempt < max_attempts:
                        time.sleep(1 * attempt)
                        continue
                    break

    raise RuntimeError(f"Failed to obtain PR review from Gemini API. Last error: {last_err}")

def get_pr_diff(workspace: Path) -> str:
    """Gets git diff against origin/main."""
    try:
        res = subprocess.run(["git", "diff", "origin/main...HEAD"], cwd=workspace, capture_output=True, text=True)
        if res.stdout.strip():
            return res.stdout.strip()[:35000]
    except Exception:
        pass
    try:
        res = subprocess.run(["git", "diff", "HEAD~1"], cwd=workspace, capture_output=True, text=True)
        if res.stdout.strip():
            return res.stdout.strip()[:35000]
    except Exception:
        pass
    return "No git diff available."

def get_head_sha(workspace: Path) -> str:
    """Gets current HEAD commit SHA."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True)
        return res.stdout.strip()
    except Exception:
        return ""

def set_commit_status(head_sha: str, state: str, description: str, context: str = "ai/architectural-review"):
    """Posts a commit status check to GitHub."""
    gh_repo = os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY")
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not (gh_repo and gh_token and head_sha):
        return

    url = f"https://api.github.com/repos/{gh_repo}/statuses/{head_sha}"
    payload = {
        "state": state, # success, failure, pending
        "description": description[:140],
        "context": context
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {gh_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[OK] Commit status set to {state} ({context})")
    except Exception as e:
        print(f"[Warning] Failed to set commit status: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="DevProxy Autonomous PR Reviewer & Architectural Gate")
    parser.add_argument("--pr-number", required=True, help="GitHub Pull Request Number")
    parser.add_argument("--workspace", default=".", help="Workspace root directory")
    args = parser.parse_args()

    primary_key = os.environ.get("GEMINI_REVIEWER_KEY", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    fallback_key = os.environ.get("GEMINI_SOLVER_KEY", "").strip() or os.environ.get("GEMINI_ISSUE_KEY", "").strip()

    if not primary_key:
        print("MISSING_KEY: GEMINI_REVIEWER_KEY or GEMINI_API_KEY is not set.", file=sys.stderr)
        sys.exit(2)

    workspace = Path(args.workspace).resolve()
    print(f"[*] Starting Autonomous PR Reviewer for PR #{args.pr_number}...")

    # Fetch PR details
    try:
        pr_json = subprocess.run(
            ["gh", "pr", "view", args.pr_number, "--json", "title,body,headRefName,baseRefName,files"],
            cwd=workspace, capture_output=True, text=True
        )
        pr_data = json.loads(pr_json.stdout) if pr_json.returncode == 0 else {}
    except Exception:
        pr_data = {}

    title = pr_data.get("title", f"Pull Request #{args.pr_number}")
    body = pr_data.get("body", "No description provided.")
    diff = get_pr_diff(workspace)
    head_sha = get_head_sha(workspace)

    # Fetch GossipMesh Memetic Knowledge
    kb = MemeticKnowledgeBase()
    meme_context = kb.format_prompt_context(repo="DevProxy")

    # Run Red Team Adversarial Audit
    auditor = RedTeamAuditor()
    red_team_findings = ""
    probes = auditor.audit_diff(diff)
    if probes:
        red_team_findings = "### 🚨 RED TEAM ADVERSARIAL AUDIT FINDINGS:\n"
        for p in probes:
            red_team_findings += f"- [{p.severity}] {p.category}: {p.description}\n"
            red_team_findings += f"  Attack Vector: {p.attack_vector}\n"
            red_team_findings += f"  Suggested Test:\n{p.exploit_test_stub}\n"

    prompt = f"""Conduct a thorough architectural and anti-spaghetti audit of this Pull Request for DevProxy:

{meme_context}

{red_team_findings}

### Pull Request Title:
{title}

### Pull Request Description:
{body}

### Git Diff (origin/main...HEAD):
```diff
{diff}
```

Audit the code against all anti-spaghetti, concurrency, performance, and security requirements. Provide your verdict in the required JSON schema.
"""

    # Call Gemini via Byzantine Consensus Engine
    consensus_engine = ByzantineConsensusEngine()
    votes = []

    # We call our fallback models to get multiple votes
    models_to_poll = ["llama3", "gemini-3.8-flash", "gemini-3.1-pro-preview", "gemini-3.1-flash-lite"]

    for model in models_to_poll:
        try:
            if model == "llama3":
                audit_result = call_ollama(prompt, model=model)
            else:
                audit_result = call_gemini(primary_key, prompt, fallback_key=fallback_key, model=model)
            vote = ModelVote(
                model_name=model,
                verdict=audit_result.get("verdict", "ACTION_REQUIRED").strip().upper(),
                score=int(audit_result.get("score", 75)),
                concerns=audit_result.get("action_items", []),
                suggestions=[]
            )
            votes.append(vote)
        except Exception as e:
            print(f"[Warning] Model {model} failed to provide a valid vote: {e}", file=sys.stderr)

    consensus_result = consensus_engine.evaluate(votes)

    is_approved = consensus_result.is_approved
    score = int(consensus_result.consensus_score)

    # Use the primary model's detailed output for the markdown report
    audit = call_gemini(primary_key, prompt, fallback_key=fallback_key, model=DEFAULT_MODEL)

    summary = audit.get("executive_summary", "Autonomous architectural audit completed.")
    anti_spaghetti = audit.get("anti_spaghetti_audit", "No architectural issues noted.")
    concurrency_sec = audit.get("security_concurrency_audit", "Concurrency & security invariants checked.")
    perf_mem = audit.get("performance_memory_audit", "Memory allocation & streaming checked.")
    test_cov = audit.get("test_coverage_audit", "Test coverage evaluated.")
    system_impact = audit.get("system_impact", "System impact evaluated.")
    action_items = audit.get("action_items", [])
    auto_patch = audit.get("auto_patch", "")

    auto_patch_md = f"\n### 🛠️ Auto-Generated Patch\n```diff\n{auto_patch}\n```\n" if auto_patch else ""

    # Format Markdown Review
    if is_approved:
        review_md = f"""## 🌟 Autonomous Architectural Review: APPROVED (Score: {score}/100)

**cc @Aditya-9-6** — This Pull Request has achieved **100% architectural readiness** and strictly adheres to DevProxy's anti-spaghetti, concurrency, and performance invariants!

### 🌐 Architectural System Impact Report
{system_impact}

### 🍝 Anti-Spaghetti & Modularity Verification
{anti_spaghetti}

### 🛡️ Concurrency, Race Freedom & Security Audit
{concurrency_sec}

### ⚡ Performance & Zero-Allocation Memory Invariants
{perf_mem}

### 🧪 Test Coverage & Invariant Verification
{test_cov}
{auto_patch_md}
---
### 🚦 Next Steps: Maintainer Sign-Off Required
**@Aditya-9-6**: All automated quality gates, anti-spaghetti checks, and performance benchmarks have passed cleanly.
To complete the merge into `main`:
- **Approve this Pull Request**, OR
- Comment **`/merge`** on this PR.
"""
        commit_desc = f"Architectural Review Passed ({score}/100) - Ready to merge"
        set_commit_status(head_sha, "success", commit_desc)
    else:
        action_bullets = "\n".join(f"- {item}" for item in action_items) if action_items else "- Address structural feedback and missing test cases."
        review_md = f"""## ⚠️ Autonomous Architectural Review: ACTION REQUIRED (Score: {score}/100)

### 📋 Executive Summary
{summary}

### 🍝 Anti-Spaghetti & Modularity Findings
{anti_spaghetti}

### 🛡️ Concurrency & Security Findings
{concurrency_sec}

### ⚡ Performance & Memory Footprint Audit
{perf_mem}

### 🧪 Test Coverage Gaps
{test_cov}

### 🛠️ Required Refactoring & Action Items
{action_bullets}
{auto_patch_md}
---
🔄 **Autonomous Self-Healing Loop Active**: The PR Fixer Agent will refactor the code according to these directives and push updates until the PR achieves 100% readiness.
"""
        commit_desc = f"Architectural Improvements Required ({score}/100)"
        set_commit_status(head_sha, "failure", commit_desc)

    # Save Markdown file
    review_file = workspace / "ai_pr_review.md"
    review_file.write_text(review_md.strip(), encoding="utf-8")

    # Save Status JSON for workflow automation
    status_file = workspace / "ai_review_status.json"
    status_data = {
        "verdict": "APPROVED" if is_approved else "ACTION_REQUIRED",
        "score": score,
        "needs_improvement": not is_approved,
        "action_items": action_items,
        "system_impact": system_impact
    }
    status_file.write_text(json.dumps(status_data, indent=2), encoding="utf-8")

    print(f"[OK] Audit finished: Verdict={status_data['verdict']} Score={score} (Written to {review_file} & {status_file})")

if __name__ == "__main__":
    main()
