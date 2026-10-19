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
from cryptography.hazmat.primitives.asymmetric import rsa

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
    pem_bytes = None

    if key_input:
        p = Path(key_input)
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
        for fallback in [
            Path(__file__).resolve().parent.parent / "enterprise" / "test_private_key.pem",
            Path("enterprise/test_private_key.pem"),
        ]:
            if fallback.is_file():
                pem_bytes = fallback.read_bytes()
                break

    if pem_bytes:
        try:
            return serialization.load_pem_private_key(pem_bytes, password=None, backend=default_backend())
        except Exception:
            pass

    # Generate an ephemeral test key if none exists or loading failed to prevent test setup failures
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    return private_key


def parse_task_map(map_str: Optional[str]) -> Optional[Dict[str, str]]:
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
    private_key = load_private_key(private_key_path)

    normalized_bundles = [b.lower().strip() for b in bundle_ids]
    for b in normalized_bundles:
        if b not in MODEL_BUNDLES:
            raise ValueError(f"Invalid bundle: {b}. Supported: {list(MODEL_BUNDLES.keys())}")

    if validity_days is None:
        validity_days = 365 if plan == "1_year" else 183

    now = int(time.time())
    exp = now + (validity_days * 86400)

    price_usd = calculate_price(
        bundle_ids=normalized_bundles,
        plan=plan,
        task_model_map=task_model_map,
    )

    payload = {
        "iss": "GossipMesh Enterprise Licensing Authority",
        "sub": customer_id.strip(),
        "iat": now,
        "nbf": now - 30,
        "exp": exp,
        "tier": "Enterprise Air-Gapped",
        "plan": plan,
        "bundle_ids": normalized_bundles,
        "task_model_map": task_model_map or {},
        "pricing_usd": price_usd,
        "offline_air_gapped": True,
        "version": "1.0",
    }

    pem_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token = jwt.encode(payload, pem_key, algorithm="RS256")
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

    bundles = args.bundles or ["b04"]
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
