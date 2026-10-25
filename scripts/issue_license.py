"""
GossipMesh Enterprise B2B License Issuing CLI
============================================
Generates offline cryptographic RSA-4096 (RS256) signed license tokens (.jwt / .token)
for high-ticket air-gapped enterprise deployments ($10K - $75K+/yr).

Usage:
    python scripts/issue_license.py \
        --customer-id "lockheed-martin-defense" \
        --bundle b04 \
        --plan 1_year \
        --private-key enterprise/test_private_key.pem \
        --output license.jwt
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Add workspace to path to import enterprise modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from enterprise.pricing import (
    MODEL_BUNDLES,
    PLAN_TERMS,
    DEFAULT_TASK_MODEL_MAP,
    CORE_TASKS,
    calculate_price,
    get_bundle,
)


def load_private_key(key_input: Optional[str] = None):
    """
    Load an RSA private key from:
    1. Direct argument (path to file or PEM string)
    2. LICENSE_PRIVATE_KEY environment variable (PEM string)
    3. LICENSE_PRIVATE_KEY_PATH environment variable (file path)
    4. enterprise/test_private_key.pem (local fallback for development)
    """
    pem_bytes = None

    if key_input:
        p = Path(key_input)
        if not p.is_file():
            # Try relative to repo root if not absolute/relative to cwd
            repo_fallback = Path(__file__).resolve().parent.parent / key_input
            if repo_fallback.is_file():
                p = repo_fallback
        if p.is_file():
            pem_bytes = p.read_bytes()
        elif "BEGIN" in key_input:
            pem_bytes = key_input.encode("utf-8")

    if not pem_bytes:
        env_raw = os.getenv("LICENSE_PRIVATE_KEY")
        if env_raw and "BEGIN" in env_raw:
            pem_bytes = env_raw.encode("utf-8")

    if not pem_bytes:
        env_path = os.getenv("LICENSE_PRIVATE_KEY_PATH")
        if env_path and Path(env_path).is_file():
            pem_bytes = Path(env_path).read_bytes()

    if not pem_bytes:
        # Search for test_private_key.pem
        current_file = Path(__file__).resolve()
        # Look in workspace root (GossipMesh/enterprise/)
        workspace_root = current_file.parent.parent
        fallback = workspace_root / "enterprise" / "test_private_key.pem"

        if fallback.is_file():
            pem_bytes = fallback.read_bytes()
        else:
            # Maybe we are in another directory? Let's check cwd
            cwd_fallback = Path.cwd() / "enterprise" / "test_private_key.pem"
            if cwd_fallback.is_file():
                pem_bytes = cwd_fallback.read_bytes()
            else:
                # Also try test_private_key.pem directly inside the same dir if somehow placed there
                same_dir = Path("test_private_key.pem")
                if same_dir.is_file():
                    pem_bytes = same_dir.read_bytes()

    if not pem_bytes:
        raise ValueError(
            "RSA private key not provided. Specify --private-key <path>, set LICENSE_PRIVATE_KEY, "
            "or set LICENSE_PRIVATE_KEY_PATH."
        )

    return serialization.load_pem_private_key(pem_bytes, password=None, backend=default_backend())


def parse_task_map(map_str: Optional[str]) -> Optional[Dict[str, str]]:
    """Parse comma-separated or JSON task-to-model mapping."""
    if not map_str:
        return None

    cleaned = map_str.strip()
    if cleaned.startswith("{"):
        parsed = json.loads(cleaned)
        return {k.strip(): v.strip().lower() for k, v in parsed.items()}

    mapping = {}
    for pair in cleaned.split(","):
        if "=" in pair:
            task, bundle = pair.split("=", 1)
            mapping[task.strip().lower()] = bundle.strip().lower()
        elif ":" in pair:
            task, bundle = pair.split(":", 1)
            mapping[task.strip().lower()] = bundle.strip().lower()
    return mapping


def issue_license(
    customer_id: str,
    bundle_ids: List[str],
    plan: str = "1_year",
    task_model_map: Optional[Dict[str, str]] = None,
    validity_days: Optional[int] = None,
    private_key_path: Optional[str] = None,
) -> str:
    """
    Generate and sign an offline RSA-4096 JWT license token.
    """
    private_key = load_private_key(private_key_path)

    # Validate bundles
    normalized_bundles = [b.lower().strip() for b in bundle_ids]
    for b in normalized_bundles:
        if b not in MODEL_BUNDLES:
            raise ValueError(f"Invalid bundle: {b}. Supported: {list(MODEL_BUNDLES.keys())}")

    # Determine validity duration
    if validity_days is None:
        validity_days = 365 if plan == "1_year" else 183

    now = int(time.time())
    exp = now + (validity_days * 86400)

    # Calculate contractual price in USD
    price_usd = calculate_price(
        bundle_ids=normalized_bundles,
        plan=plan,
        task_model_map=task_model_map,
    )

    payload = {
        "iss": "GossipMesh Enterprise Licensing Authority",
        "sub": customer_id.strip(),
        "iat": now,
        "nbf": now - 30,  # 30-second clock skew allowance
        "exp": exp,
        "tier": "Enterprise Air-Gapped",
        "plan": plan,
        "bundle_ids": normalized_bundles,
        "task_model_map": task_model_map or {},
        "pricing_usd": price_usd,
        "offline_air_gapped": True,
        "version": "1.0",
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token


def main():
    parser = argparse.ArgumentParser(description="Issue offline RSA-4096 signed JWT enterprise license tokens.")
    parser.add_argument("--customer-id", required=True, help="Customer ID (e.g., acme-fintech-corp)")
    parser.add_argument(
        "--bundle",
        action="append",
        dest="bundles",
        help="Model bundle ID (b01, b02, b03, b04, b05). Can specify multiple times.",
    )
    parser.add_argument(
        "--plan",
        choices=["1_year", "6_months"],
        default="1_year",
        help="Subscription term (default: 1_year)",
    )
    parser.add_argument(
        "--task-map",
        help="Task-to-model map, e.g. 'syntax=b01,security=b04,architecture=b04,auto_remediation=b05'",
    )
    parser.add_argument(
        "--private-key",
        help="Path to RSA private key PEM file.",
    )
    parser.add_argument(
        "--validity-days",
        type=int,
        help="Custom validity in days (overrides default plan duration).",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="File path to save license token (e.g. license.jwt). If omitted, prints to stdout.",
    )

    args = parser.parse_args()

    bundles = args.bundles or ["b04"]  # Default to flagship $50K Enterprise tier
    task_map = parse_task_map(args.task_map)

    token = issue_license(
        customer_id=args.customer_id,
        bundle_ids=bundles,
        plan=args.plan,
        task_model_map=task_map,
        validity_days=args.validity_days,
        private_key_path=args.private_key,
    )

    price = calculate_price(bundles, args.plan, task_map)
    print("=" * 60)
    print(" GOSSIPMESH ENTERPRISE LICENSE GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f" Customer ID   : {args.customer_id}")
    print(f" Plan          : {args.plan}")
    print(f" Bundle(s)     : {', '.join(bundles)}")
    if task_map:
        print(f" Task Mapping  : {json.dumps(task_map)}")
    print(f" Contract Price: ${price:,} USD")
    print("=" * 60)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.write_text(token, encoding="utf-8")
        print(f"License saved to: {out_path}\n")
    else:
        print("\nToken:\n")
        print(token)
        print()


if __name__ == "__main__":
    main()
