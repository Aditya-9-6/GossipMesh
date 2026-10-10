#!/usr/bin/env python3
"""
GossipMesh Architecture Advancement Issue Generator Engine
Autonomous issue generator bot for continuous open-source contribution & architectural advancement.
Features:
- Curated high-impact systems engineering catalog
- Dynamic Gemini AI generation with strict anti-spaghetti prompts
- Freeze timer & cooldown protection to prevent GitHub secondary rate-limit breaks
- Local backlog queue archiving when cooldown is active
- Mandatory anti-spaghetti warnings and architectural quality criteria
"""

import json
import subprocess
import os

import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-3.1-pro-preview"]

# Curated catalog of high-impact open-source architecture advancements for GossipMesh (Python)
CATALOG = [
    {
        "title": "feat(p2p): Implement Kademlia DHT for Peer Discovery",
        "area": "area/p2p",
        "difficulty": "enhancement",
        "spec": "Replace static peer configuration with a distributed hash table (DHT) based on Kademlia. Implement XOR metric routing and bucket updates for active peers.",
        "target_files": ["gossipmesh/p2p/dht.py", "gossipmesh/p2p/node.py"]
    },
    {
        "title": "feat(consensus): Add Byzantine Fault Tolerant (BFT) Voting Quorum",
        "area": "area/consensus",
        "difficulty": "priority/high",
        "spec": "Implement a 2/3 majority BFT voting mechanism for architectural proposals. Ensure that malicious or lagging nodes cannot disrupt the consensus state.",
        "target_files": ["gossipmesh/consensus/bft.py", "tests/test_bft.py"]
    },
    {
        "title": "feat(agents): Integrate Local LLM Fallback via Llama.cpp",
        "area": "area/agents",
        "difficulty": "good first issue",
        "spec": "Add a fallback completion provider that uses local Llama.cpp bindings when the Gemini API is rate-limited or unavailable, preserving autonomy.",
        "target_files": ["gossipmesh/agents/llm.py"]
    },
    {
        "title": "feat(core): Zero-Copy Vector Clock Synchronization",
        "area": "area/core",
        "difficulty": "enhancement",
        "spec": "Optimize the vector clock anti-entropy sync using efficient delta encodings and avoiding deep copies of the state ledger during peer exchanges.",
        "target_files": ["gossipmesh/core/clocks.py", "tests/test_clocks.py"]
    }
]

def get_existing_issues():
    """Fetch existing issue titles and creation timestamps."""
    issues_info = []
    try:
        cmd = ["gh", "issue", "list", "--repo", "Aditya-9-6/GossipMesh", "--state", "all", "--limit", "100", "--json", "title,createdAt,author"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issues = json.loads(result.stdout)
        return issues
    except Exception as e:
        print(f"[WARN] Failed to fetch issues via gh CLI: {e}")
        return []

def check_freeze_timer(existing_issues, cooldown_minutes=0, force=False):
    """
    Checks if an advancement issue was submitted recently.
    Returns (can_submit: bool, minutes_elapsed: float)
    """
    if force:
        return True, 999.0

    now = datetime.now(timezone.utc)
    for issue in existing_issues:
        created_at_str = issue.get("createdAt")
        if not created_at_str:
            continue
        try:
            # Parse ISO 8601
            dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            elapsed = (now - dt).total_seconds() / 60.0
            if elapsed < cooldown_minutes:
                return False, elapsed
        except Exception:
            pass
        # Only inspect the most recent issue
        break

    return True, 999.0

def load_backlog(workspace: Path) -> list:
    """Loads archived backlog queue from file."""
    backlog_file = workspace / ".github" / "advancement_backlog.json"
    if backlog_file.is_file():
        try:
            return json.loads(backlog_file.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_backlog(workspace: Path, backlog: list):
    """Saves backlog queue to file."""
    backlog_file = workspace / ".github" / "advancement_backlog.json"
    backlog_file.parent.mkdir(parents=True, exist_ok=True)
    backlog_file.write_text(json.dumps(backlog, indent=2), encoding="utf-8")

def generate_ai_advancement(existing_titles):
    """Use Gemini API to dynamically generate a novel, high-impact architectural advancement task."""
    api_key = os.environ.get("GEMINI_ISSUE_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    prompt = f"""You are the Principal Systems Software Architect of GossipMesh, a Decentralized P2P Gossip Protocol Multi-Agent Autonomous Engineering Mesh written in Python.

Create a brand new, novel, high-impact systems engineering task for open-source contributors.

STRICT QUALITY INVARIANTS (ANTI-POISONING):
1. NO TRIVIAL CHORES: Do NOT generate documentation fixes, typo corrections, dependency bumps, cosmetic UI adjustments, or trivial variable renames.
2. POSITIVE SYSTEM IMPACT ONLY: You MUST NOT propose any feature that introduces unnecessary dependencies, bloat, highly speculative ideas, or experimental toys that do not directly improve production stability, performance, or core decentralization properties.
3. ANTI-SPAGHETTI DESIGN: Every feature must specify clean package decoupling, single-responsibility functions (<60 LOC), and zero circular dependencies. Avoid God classes and massive God functions. Propose solutions that increase modularity, not decrease it.
4. PRODUCTION SYSTEMS FOCUS: Tasks must involve P2P networking, multi-agent systems, byzantine consensus, distributed ledgers, or AI prompt engineering.

DO NOT duplicate any of these existing titles:
{json.dumps(list(existing_titles)[:30], indent=2)}

Output ONLY valid JSON matching this schema:
{{
  "title": "feat(subsystem): Concise descriptive title",
  "area": "area/p2p" or "area/consensus" or "area/agents" or "area/cli" or "area/core",
  "difficulty": "good first issue" or "enhancement" or "priority/high",
  "spec": "Clear 3-4 sentence technical specification outlining what to implement, performance invariants, and target packages.",
  "target_files": ["gossipmesh/...", "tests/..."]
}}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}
    }

    for model in FALLBACK_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        for attempt in range(1, 4):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    freeze_sec = 5 * attempt
                    print(f"[FREEZE TIMER] Rate limit encountered on {model}. Backing off for {freeze_sec}s...", flush=True)
                    time.sleep(freeze_sec)
                    continue
                break
            except Exception as e:
                print(f"[WARN] Error with {model}: {e}")
                break
    return None

def create_issue(item):
    """Create a structured GitHub issue with strict anti-spaghetti warnings."""
    title = item["title"]
    area = item.get("area", "area/p2p")
    difficulty = item.get("difficulty", "good first issue")
    spec = item["spec"]
    target_files = item.get("target_files", [])

    target_files_md = "\n".join(f"- `{f}`" for f in target_files) if target_files else "- Relevant files in `gossipmesh/`"

    body = f"""## 🚀 Architecture Advancement Specification

### 📌 Overview & Rationale
{spec}

### 🎯 Subsystem & Domain
- **Domain**: `{area}`
- **Difficulty**: `{difficulty}`
- **Initiative**: Hacktoberfest / Sovereign High-Performance GossipMesh Advancement

### 📂 Target Files & Modules
{target_files_md}

### 📋 Technical Acceptance Criteria
- [ ] Conforms to GossipMesh's zero-allocation streaming patterns (utilize `sync.Pool` for buffers).
- [ ] Maintains deterministic performance ($O(1)$ lookup or $O(N)$ streaming throughput).
- [ ] Concurrency safety verified: zero data races, proper mutex/atomic synchronization, no goroutine leaks on context cancellation.
### 📋 Technical Acceptance Criteria & Architectural Sanity Checklist
- [ ] Conforms to GossipMesh's robust Python engineering patterns.
- [ ] Feature has a positive system impact and does not introduce bloat, unnecessary dependencies, or highly speculative experimental code.
- [ ] Concurrency safety verified: proper async/await usage if applicable, zero data races.
- [ ] Unit tests added covering normal operation, boundary conditions, and error branches.
- [ ] Code formatted with `black` and static checks clean (`flake8 .`).

---

### 🍝 Anti-Spaghetti Code & Anti-Poisoning Warning
> ⚠️ **STRICT CODE REVIEWER STANDARDS**: Any implementation that introduces spaghetti code, architectural regressions, or negative system impacts will be automatically rejected by the Autonomous Reviewer Bot!
> 
> - **Modular Architecture**: Keep functions concise (<60 LOC), single-purpose, and decoupled across `gossipmesh/` modules. No God classes.
> - **Dependency Hygiene**: Do not introduce heavy or unnecessary third-party dependencies unless strictly required for core functionality.
> - **Zero Data Races**: Enforce thread/async safety.
> - **Comprehensive Tests**: Provide comprehensive Python unit tests covering happy paths, edge cases, and error branches.

### 🛠️ Getting Started
1. Fork the repository and create a branch: `git checkout -b feature/{area.replace('area/', '')}-advancement`
2. Run local tests: `python -m unittest discover`
3. When ready, open a PR. Comment `@gossipmesh-bot solve` or `/solve` to ask the AI assistant for scaffolding, or submit your solution for automated review!
"""

    labels = f"{area},{difficulty},hacktoberfest,advancement"
    cmd = [
        "gh", "issue", "create", "--repo", "Aditya-9-6/GossipMesh",
        "--title", title,
        "--body", body,
        "--label", labels
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[SUCCESS] Created issue: {result.stdout.strip()} - {title}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to create issue '{title}': {e.stderr}")
        return False

def main():
    workspace = Path(".").resolve()
    manual_title = os.environ.get("INPUT_TITLE", "").strip()
    manual_area = os.environ.get("INPUT_AREA", "auto").strip()
    manual_diff = os.environ.get("INPUT_DIFFICULTY", "good first issue").strip()
    manual_spec = os.environ.get("INPUT_SPEC", "").strip()
    count = int(os.environ.get("INPUT_COUNT", "1") or "1")
    cooldown_min = int(os.environ.get("MIN_COOLDOWN_MINUTES", "0"))
    force = os.environ.get("FORCE_SUBMIT", "false").lower() in ("true", "1") or ("--force" in sys.argv) or ("-f" in sys.argv)

    # If manual submission specified
    if manual_title and manual_area != "auto":
        create_issue({
            "title": manual_title,
            "area": manual_area,
            "difficulty": manual_diff,
            "spec": manual_spec or f"Implement architectural advancement for {manual_title}."
        })
        return

    existing_issues = get_existing_issues()
    existing_titles = {i["title"].strip() for i in existing_issues if "title" in i}
    print(f"[*] Found {len(existing_titles)} existing issues in repository.")

    # 1. Check Freeze Timer Cooldown
    can_submit, elapsed = check_freeze_timer(existing_issues, cooldown_minutes=cooldown_min, force=force)
    if not can_submit:
        print(f"[FREEZE TIMER ACTIVE] Last issue was created {elapsed:.1f} minutes ago (< {cooldown_min} min cooldown).")
        print("[*] Generating next high-impact advancement and archiving to backlog queue to prevent rate-limit breaks...")

        # Find next candidate to archive
        candidate = None
        for item in CATALOG:
            if item["title"] not in existing_titles:
                candidate = item
                break
        if not candidate:
            candidate = generate_ai_advancement(existing_titles)

        if candidate:
            backlog = load_backlog(workspace)
            if not any(b["title"] == candidate["title"] for b in backlog):
                backlog.append(candidate)
                save_backlog(workspace, backlog)
                print(f"[ARCHIVED TO BACKLOG] Stored: '{candidate['title']}'. Will be submitted once freeze timer expires.")
        return

    # 2. Cooldown is clear: Drain backlog first if available
    backlog = load_backlog(workspace)
    created_count = 0

    while backlog and created_count < count:
        item = backlog.pop(0)
        if item["title"] not in existing_titles:
            print(f"[*] Submitting archived backlog item: '{item['title']}'...")
            if create_issue(item):
                existing_titles.add(item["title"])
                created_count += 1
                save_backlog(workspace, backlog)
                if created_count < count:
                    print("[RATE-LIMIT DELAY] Sleeping 1s to protect GitHub secondary rate limit...")
                    time.sleep(1)

    # 3. Pull from curated catalog
    for item in CATALOG:
        if created_count >= count:
            break
        if item["title"] not in existing_titles:
            if create_issue(item):
                existing_titles.add(item["title"])
                created_count += 1
                if created_count < count:
                    print("[RATE-LIMIT DELAY] Sleeping 1s to protect GitHub secondary rate limit...")
                    time.sleep(1)

    # 4. If catalog exhausted and more requested, dynamically generate via Gemini AI
    if created_count < count:
        print(f"[*] Catalog exhausted or more issues requested ({created_count}/{count}). Querying Gemini AI for novel advancement...")
        while created_count < count:
            ai_item = generate_ai_advancement(existing_titles)
            if not ai_item or ai_item.get("title") in existing_titles:
                print("[!] Could not generate further unique dynamic issues.")
                break
            if create_issue(ai_item):
                existing_titles.add(ai_item["title"])
                created_count += 1
                if created_count < count:
                    print("[RATE-LIMIT DELAY] Sleeping 1s to protect GitHub secondary rate limit...")
                    time.sleep(1)

    if created_count == 0:
        print("[OK] No new issues needed or all catalog items already exist.")
    else:
        print(f"[DONE] Successfully generated {created_count} advancement issue(s) under safe rate-limiting.")

if __name__ == "__main__":
    main()
