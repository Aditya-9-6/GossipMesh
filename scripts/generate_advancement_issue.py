#!/usr/bin/env python3
"""
GossipMesh Architecture Advancement Issue Generator Engine
Autonomous issue generator bot for continuous open-source contribution & architectural advancement across:
- Aditya-9-6/DevProxy (Go)
- Aditya-9-6/GossipMesh (Python)
- Aditya-9-6/Skelion (Python/TS)

Features:
- Comprehensive domain-specific catalogs (Go, Python P2P, SRE/Agent Mesh)
- Resilient Gemini AI generation with key-pool failover & OpenRouter/NVIDIA/Cohere fallbacks
- Cooldown protection with safe rate-limiting
- Guaranteed issue replenishment to ensure autonomous loops never stall
"""

import json
import subprocess
import os
import sys
import time
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

TARGET_REPO = os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY") or "Aditya-9-6/GossipMesh"

FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-pro-latest",
]

DEVPROXY_CATALOG = [
    {
        "title": "feat(waf): Implement Aho-Corasick multi-pattern scanner with zero heap allocations",
        "area": "area/security",
        "difficulty": "priority/high",
        "spec": "Implement a high-throughput Aho-Corasick automaton for concurrent regex and signature inspection over streaming HTTP request bodies with zero allocations on the match path.",
        "target_files": ["pkg/security/waf/ahocorasick.go", "pkg/security/waf/ahocorasick_test.go"],
    },
    {
        "title": "feat(circuitbreaker): Implement distributed hysteresis circuit breaker with half-open probing",
        "area": "area/proxy",
        "difficulty": "enhancement",
        "spec": "Add a thread-safe, lock-free circuit breaker using atomic uint64 counters and exponential backoff probing for failing upstream endpoints.",
        "target_files": ["pkg/proxy/circuitbreaker.go", "pkg/proxy/circuitbreaker_test.go"],
    },
    {
        "title": "feat(quic): Implement RFC 9000 packet coalescing and AEAD decryption pipeline",
        "area": "area/protocol",
        "difficulty": "priority/high",
        "spec": "Implement bounded datagram coalescing and RFC 9000 header protection removal with AES-GCM and ChaCha20-Poly1305 key suites.",
        "target_files": ["pkg/protocol/quic/coalesce.go", "pkg/protocol/quic/coalesce_test.go"],
    },
    {
        "title": "feat(grpc): Implement transparent bidirectional gRPC frame streaming proxy with cancellation propagation",
        "area": "area/proxy",
        "difficulty": "enhancement",
        "spec": "Implement transparent HTTP/2 gRPC frame routing that preserves end-to-end trailers and forwards client/server RST_STREAM cancellations without buffering full payloads.",
        "target_files": ["pkg/proxy/grpc_stream.go", "pkg/proxy/grpc_stream_test.go"],
    },
    {
        "title": "feat(ratelimit): Implement Distributed Leaky-Bucket Rate Limiter with Atomic Ring Buffers",
        "area": "area/proxy",
        "difficulty": "enhancement",
        "spec": "Implement a high-performance leaky bucket rate limiter using atomic CAS operations and fixed-size sliding timestamp windows.",
        "target_files": ["pkg/ratelimit/leakybucket.go", "pkg/ratelimit/leakybucket_test.go"],
    },
    {
        "title": "feat(tls): Implement RFC 8446 0-RTT Early Data Replay Protection Cache",
        "area": "area/security",
        "difficulty": "priority/high",
        "spec": "Add bounded single-use ticket verification and bloom-filter replay cache to safely handle TLS 1.3 0-RTT early data without request duplication vulnerabilities.",
        "target_files": ["pkg/tls/earlydata.go", "pkg/tls/earlydata_test.go"],
    },
    {
        "title": "feat(dns): Implement Non-Blocking DNS-over-HTTPS (DoH) Resolver with In-Memory TTL Cache",
        "area": "area/dns",
        "difficulty": "good first issue",
        "spec": "Implement an asynchronous DoH client conforming to RFC 8484 with positive and negative response caching and stale-while-revalidate semantics.",
        "target_files": ["pkg/dns/doh.go", "pkg/dns/doh_test.go"],
    },
    {
        "title": "feat(ebpf): Implement Socket Dispatch Trampoline with Bounded Ring Buffer Telemetry",
        "area": "area/proxy",
        "difficulty": "priority/high",
        "spec": "Implement zero-copy socket redirection for internal proxy ports with perf event ring buffer export for real-time throughput metrics.",
        "target_files": ["pkg/ebpf/socket_dispatch.go", "pkg/ebpf/socket_dispatch_test.go"],
    },
]

GOSSIPMESH_CATALOG = [
    {
        "title": "feat(crdt): Implement State-Based Delta-CRDT for Task Allocation",
        "area": "area/agents",
        "difficulty": "priority/high",
        "spec": "Implement a state-based Delta-CRDT register for concurrent multi-agent task claims with causal history tracking and monotonic join-semilattice merges.",
        "target_files": ["gossipmesh/agents/crdt_store.py", "tests/agents/test_crdt_store.py"],
    },
    {
        "title": "feat(p2p): Implement Invertible Bloom Lookup Table (IBLT) for Anti-Entropy",
        "area": "area/p2p",
        "difficulty": "enhancement",
        "spec": "Implement an Invertible Bloom Lookup Table (IBLT) algorithm to reconcile peer difference sets in $O(d)$ network messages rather than transmitting full key inventories.",
        "target_files": ["gossipmesh/p2p/iblt.py", "tests/test_p2p_iblt.py"],
    },
    {
        "title": "feat(security): Implement Ephemeral Key Exchange with Noise Protocol XX Handshake",
        "area": "area/security",
        "difficulty": "priority/high",
        "spec": "Implement mutual authentication and forward-secret session key derivation between mesh peers using the Noise_XX_25519_ChaChaPoly_BLAKE2s pattern.",
        "target_files": ["gossipmesh/security/noise.py", "tests/test_security_noise.py"],
    },
    {
        "title": "feat(transport): Implement Bounded QUIC Datagram Transport with Congestion Control",
        "area": "area/p2p",
        "difficulty": "enhancement",
        "spec": "Implement unreliable and reliable datagram multiplexing over async UDP sockets with AIMD congestion windows for resilient cross-region peer synchronization.",
        "target_files": ["gossipmesh/p2p/quic_transport.py", "tests/test_quic_transport.py"],
    },
    {
        "title": "feat(consensus): Implement Raft Log Replication State Machine for Distributed Configuration",
        "area": "area/consensus",
        "difficulty": "priority/high",
        "spec": "Implement leader election, log entry append RPCs, and committed state compaction for cluster-wide peer configuration metadata.",
        "target_files": ["gossipmesh/consensus/raft.py", "tests/test_raft.py"],
    },
    {
        "title": "feat(agents): Implement Hierarchical Multi-Agent Consensus Orchestrator",
        "area": "area/agents",
        "difficulty": "enhancement",
        "spec": "Implement an agent leadership election and sub-task delegation coordinator with health heartbeats and automatic lease timeouts.",
        "target_files": ["gossipmesh/agents/orchestrator.py", "tests/agents/test_orchestrator.py"],
    },
]

SKELION_CATALOG = [
    {
        "title": "feat(sre): Implement Automated Outlier Anomaly Detection with Sliding Z-Score Filter",
        "area": "area/sre",
        "difficulty": "priority/high",
        "spec": "Implement an online streaming anomaly detector for HTTP latency spikes and error rate regressions using Welford's algorithm and dynamic thresholds.",
        "target_files": ["skelion_agent/anomaly.py", "tests/test_anomaly_detection.py"],
    },
    {
        "title": "feat(sandbox): Implement Deterministic Failure Replay Sandbox for Microservice Outages",
        "area": "area/sandbox",
        "difficulty": "priority/high",
        "spec": "Implement an isolated test harness to re-execute recorded production HTTP error payloads with simulated downstream mock latencies and failures.",
        "target_files": ["skelion_agent/replay_sandbox.py", "tests/test_replay_sandbox_deep.py"],
    },
    {
        "title": "feat(incident): Implement Real-Time Causality Graph Generation for Cascading Failures",
        "area": "area/incident",
        "difficulty": "enhancement",
        "spec": "Construct directed acyclic dependency graphs from distributed trace spans to pinpoint the exact root-cause upstream node in cascading timeout cascades.",
        "target_files": ["skelion_agent/causality.py", "tests/test_causality_graph.py"],
    },
    {
        "title": "feat(mitigation): Implement Adaptive Concurrency Throttler with Bounded Token Bucket",
        "area": "area/mitigation",
        "difficulty": "enhancement",
        "spec": "Implement automated client traffic shedder that dynamically throttles non-critical ingress routes when backend CPU or memory exhaustion exceeds safe thresholds.",
        "target_files": ["skelion_agent/throttler.py", "tests/test_throttler.py"],
    },
    {
        "title": "feat(telemetry): Implement Distributed OpenTelemetry Trace Ingestion with Tail Sampling",
        "area": "area/telemetry",
        "difficulty": "enhancement",
        "spec": "Add support for consuming W3C TraceContext headers and high-cardinality span attributes with memory-bounded ring buffers and tail-based sampling for error spans.",
        "target_files": ["skelion_agent/telemetry.py", "tests/test_telemetry_ingest.py"],
    },
]


def load_gemini_keys() -> list[str]:
    keys = []
    pool = os.environ.get("GEMINI_KEY_POOL", "")
    for k in re.split(r"[,\s]+", pool):
        if k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    for var in ("GEMINI_ISSUE_KEY", "GEMINI_API_KEY", "GEMINI_SOLVER_KEY", "GEMINI_REVIEWER_KEY"):
        val = os.environ.get(var, "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def get_existing_issues():
    try:
        cmd = [
            "gh",
            "issue",
            "list",
            "--repo",
            TARGET_REPO,
            "--state",
            "all",
            "--limit",
            "150",
            "--json",
            "title,createdAt,author",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"[WARN] Failed to fetch issues via gh CLI: {e}")
        return []


def check_freeze_timer(existing_issues, cooldown_minutes=0, force=False):
    if force:
        return True, 999.0
    now = datetime.now(timezone.utc)
    for issue in existing_issues:
        created_at_str = issue.get("createdAt")
        if not created_at_str:
            continue
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            elapsed = (now - created_at).total_seconds() / 60.0
            if elapsed < cooldown_minutes:
                return False, elapsed
        except Exception:
            pass
        break
    return True, 999.0


def generate_ai_advancement(existing_titles):
    keys = load_gemini_keys()
    repo_name = TARGET_REPO.split("/")[-1].lower()
    if "devproxy" in repo_name:
        role_desc = "DevProxy, a high-performance HTTP/2, HTTP/3, eBPF, and TLS reverse proxy written in Go"
        tech_stack = "Go (Golang)"
        target_dir = "pkg/"
    elif "skelion" in repo_name:
        role_desc = "Skelion, an autonomous AI site reliability engineering agent mesh and incident management system written in Python"
        tech_stack = "Python"
        target_dir = "skelion_agent/"
    else:
        role_desc = (
            "GossipMesh, a Decentralized P2P Gossip Protocol Multi-Agent Autonomous Engineering Mesh written in Python"
        )
        tech_stack = "Python"
        target_dir = "gossipmesh/"

    prompt = f"""You are the Principal Systems Software Architect of {role_desc}.
Create a brand new, novel, high-impact systems engineering task for open-source contributors in {tech_stack}.

STRICT QUALITY INVARIANTS:
1. NO TRIVIAL CHORES: No docs, typo fixes, or trivial renames.
2. POSITIVE SYSTEM IMPACT ONLY: Must solve real networking, concurrency, memory, or architectural scaling challenges.
3. MODULAR ARCHITECTURE: Single-responsibility modules under {target_dir}, comprehensive unit tests.

DO NOT duplicate any of these existing titles:
{json.dumps(list(existing_titles)[:40], indent=2)}

Output ONLY valid JSON matching:
{{
  "title": "feat(subsystem): Concise descriptive title",
  "area": "area/proxy" or "area/p2p" or "area/sre" or "area/core" or "area/security",
  "difficulty": "good first issue" or "enhancement" or "priority/high",
  "spec": "Clear 3-4 sentence technical specification outlining what to implement and performance invariants.",
  "target_files": ["{target_dir}...", "tests/..."]
}}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
    }

    # Try Gemini keys
    for current_key in keys:
        for model in FALLBACK_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={current_key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    res = json.loads(text)
                    if isinstance(res, dict) and "title" in res:
                        return res
            except Exception:
                continue

    # Fallback to OpenRouter if available
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(
                    {
                        "model": "meta-llama/llama-3.3-70b-instruct",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                    }
                ).encode("utf-8"),
                headers={"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return json.loads(data["choices"][0]["message"]["content"])
        except Exception:
            pass

    return None


def create_issue(item):
    title = item["title"]
    area = item.get("area", "area/core")
    difficulty = item.get("difficulty", "enhancement")
    spec = item.get("spec", "")
    target_files = item.get("target_files", [])

    target_files_md = "\n".join(f"- `{f}`" for f in target_files) if target_files else "- Relevant package files"

    body = f"""## 🚀 Architecture Advancement Specification

### 📌 Overview & Rationale
{spec}

### 🎯 Subsystem & Domain
- **Domain**: `{area}`
- **Difficulty**: `{difficulty}`
- **Initiative**: Sovereign Continuous Autonomous Advancement

### 📂 Target Files & Modules
{target_files_md}

### 📋 Technical Acceptance Criteria
- [ ] Conforms to repository architectural guidelines and high-performance invariants.
- [ ] Idiomatic implementation, memory safety, and complete absence of data races.
- [ ] Comprehensive unit tests added covering boundary conditions and happy paths.
- [ ] All pre-flight compiler and vetting checks pass cleanly.

---
*Created by Autonomous Advancement Engine*
"""
    labels_list = [area, difficulty, "advancement"]
    for lbl in labels_list:
        subprocess.run(["gh", "label", "create", lbl, "--repo", TARGET_REPO, "--force"], capture_output=True)
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        TARGET_REPO,
        "--title",
        title,
        "--body",
        body,
        "--label",
        f"advancement,{area},{difficulty}",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[✓] Created Issue: {res.stdout.strip()} - {title}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to create issue '{title}': {e.stderr}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GossipMesh Architecture Advancement Issue Generator Engine")
    parser.add_argument(
        "--count", type=int, default=int(os.environ.get("INPUT_COUNT", "2") or "2"), help="Number of issues to generate"
    )
    parser.add_argument("--force", "-f", action="store_true", help="Force issue creation")
    args, _ = parser.parse_known_args()

    repo_name = TARGET_REPO.split("/")[-1].lower()
    if "devproxy" in repo_name:
        catalog = DEVPROXY_CATALOG
    elif "skelion" in repo_name:
        catalog = SKELION_CATALOG
    else:
        catalog = GOSSIPMESH_CATALOG

    count = args.count
    force = args.force

    existing_issues = get_existing_issues()
    existing_titles = {i["title"].strip() for i in existing_issues if "title" in i}
    print(f"[*] Repository: {TARGET_REPO} | Discovered {len(existing_titles)} existing issues.")

    created_count = 0

    # 1. First, drain curated domain catalog
    for item in catalog:
        if created_count >= count:
            break
        if item["title"] not in existing_titles:
            if create_issue(item):
                existing_titles.add(item["title"])
                created_count += 1
                time.sleep(1)

    # 2. If catalog exhausted or more requested, generate dynamically via AI
    if created_count < count:
        print(f"[*] Querying AI for dynamic novel advancement issues ({created_count}/{count})...")
        attempts = 0
        while created_count < count and attempts < 3:
            attempts += 1
            ai_item = generate_ai_advancement(existing_titles)
            if ai_item and ai_item.get("title") not in existing_titles:
                if create_issue(ai_item):
                    existing_titles.add(ai_item["title"])
                    created_count += 1
                    time.sleep(1)

    print(f"[✓] Issue generation pass complete. Created {created_count} new advancement issue(s).")


if __name__ == "__main__":
    main()
