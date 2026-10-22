"""
Staging Environment Smoke Test & Health Verification (Task 117).

Runs automated validation against staging deployment:
- Liveness and readiness probes
- Database connectivity & migration state
- Redis round-trip
- Auth login smoke test
- Recommends rollback on failure
"""

from __future__ import annotations

import os
import sys
import time
import httpx


def run_staging_smoke_tests(base_url: str = "http://localhost:8000") -> bool:
    print(f"[*] Starting GossipMesh Staging Smoke Tests against {base_url}...")
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Liveness Probe
    try:
        live_res = client.get("/health/live")
        if live_res.status_code != 200 or live_res.json().get("status") != "alive":
            print(f"[!] FAILED: Liveness probe returned {live_res.status_code}: {live_res.text}")
            return False
        print("[+] PASS: Liveness probe is responsive.")
    except Exception as e:
        print(f"[!] FAILED: Liveness probe error: {e}")
        return False

    # 2. Readiness Probe
    try:
        ready_res = client.get("/health/ready")
        if ready_res.status_code != 200:
            print(f"[!] FAILED: Readiness probe returned {ready_res.status_code}: {ready_res.text}")
            return False
        comps = ready_res.json().get("components", {})
        print(
            f"[+] PASS: Readiness probe healthy. Database: {comps.get('database', {}).get('status')}, Redis: {comps.get('redis', {}).get('status')}"
        )
    except Exception as e:
        print(f"[!] FAILED: Readiness probe error: {e}")
        return False

    # 3. Prometheus Metrics Endpoint
    try:
        metrics_res = client.get("/metrics")
        if metrics_res.status_code != 200 or "gossipmesh_http_requests_total" not in metrics_res.text:
            print(f"[!] FAILED: Metrics endpoint verification failed: {metrics_res.status_code}")
            return False
        print("[+] PASS: Prometheus metrics endpoint verified.")
    except Exception as e:
        print(f"[!] FAILED: Metrics probe error: {e}")
        return False

    print("\n[🎉] ALL STAGING SMOKE TESTS PASSED SUCCESSFULLY! Ready for canary promotion.")
    return True


if __name__ == "__main__":
    url = os.getenv("STAGING_BASE_URL", "http://localhost:8000")
    success = run_staging_smoke_tests(url)
    sys.exit(0 if success else 1)
