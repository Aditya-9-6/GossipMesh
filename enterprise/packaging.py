"""
GossipMesh Enterprise AI Reviewer Packaging CLI
==============================================
CLI entry-point for the air-gapped Docker container deployment.
Performs offline RSA-4096 cryptographic license validation, resolves
parameter-tiered model bundles, runs the infrastructure-aware code reviewer,
and optionally emits HMAC-signed SaaS telemetry.

Usage:
    python -m enterprise.packaging --repo-path /workspace
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional

from enterprise.licensing import (
    verify_license,
    get_bundle_for_task,
    LicenseError,
    LicenseMissingError,
    LicenseExpiredError,
    LicenseInvalidError,
    BundleNotAuthorizedError,
)
from enterprise.pricing import MODEL_BUNDLES, CORE_TASKS, TASK_ARCHITECTURE
from enterprise.telemetry import report_telemetry_event, is_telemetry_enabled


def resolve_model_directory(bundle_id: str, base_model_dir: Path) -> Path:
    """Find the specific model directory for a bundle ID."""
    bundle_meta = MODEL_BUNDLES.get(bundle_id, {})
    expected_subdir = bundle_meta.get("default_dir")

    # 1. Check if base_model_dir itself contains model files
    if (base_model_dir / "model.bin").is_file() or (base_model_dir / "config.json").is_file():
        return base_model_dir

    # 2. Check subdirectory (e.g. models/b04_qwen2.5_coder_14b)
    if expected_subdir:
        candidate = base_model_dir / Path(expected_subdir).name
        if candidate.is_dir():
            return candidate

    # 3. Search for any directory starting with bundle_id
    for child in base_model_dir.glob(f"{bundle_id}*"):
        if child.is_dir():
            return child

    # Fallback to base_model_dir
    return base_model_dir


def format_report_text(
    license_data: Dict[str, Any],
    bundle_id: str,
    task: str,
    review_result: Dict[str, Any],
) -> str:
    """Generate a clean, professional text report for developers and security audits."""
    bundle_info = MODEL_BUNDLES.get(bundle_id, {"name": bundle_id, "parameters": "N/A"})
    score = review_result["score"]
    grade = review_result["grade"]
    findings = review_result["findings"]

    lines = [
        "=" * 72,
        "   GOSSIPMESH ENTERPRISE INFRASTRUCTURE & ARCHITECTURE REVIEW",
        "=" * 72,
        f" Customer       : {license_data.get('sub', 'Unknown')}",
        f" License Tier   : {license_data.get('tier', 'Enterprise')} ({license_data.get('plan', 'Annual')})",
        f" Active Model   : {bundle_info.get('name')} [{bundle_info.get('parameters')}] (Bundle {bundle_id.upper()})",
        f" Evaluation Task: {task.upper()}",
        f" Deployment Mode: {'Strict Air-Gapped (Offline)' if not is_telemetry_enabled() else 'Connected SaaS'}",
        "-" * 72,
        f" INFRASTRUCTURE SCORE : {score}/100    [GRADE: {grade}]",
        f" Files Scanned        : {review_result['files_scanned']}",
        f" Total Findings       : {review_result['total_findings']}",
        f" Breakdown            : Critical: {review_result['severity_summary']['critical']} | "
        f"High: {review_result['severity_summary']['high']} | "
        f"Medium: {review_result['severity_summary']['medium']} | "
        f"Low: {review_result['severity_summary']['low']}",
        "=" * 72,
    ]

    if not findings:
        lines.append("  [+] No infrastructure security issues or architectural anti-patterns detected.")
    else:
        lines.append("\nDIAGNOSTIC FINDINGS & REMEDIATION:")
        for idx, f in enumerate(findings, start=1):
            lines.extend(
                [
                    f"\n[{idx}] {f['severity'].upper()} - {f['rule_id']} at {f['file']}:{f['line']}",
                    f"    Issue      : {f['message']}",
                    f"    Remediation: {f['remediation']}",
                ]
            )

    lines.append("\n" + "=" * 72)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GossipMesh Enterprise Air-Gapped Code & Infrastructure Reviewer.")
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to repository root to review (default: current directory).",
    )
    parser.add_argument(
        "--model-dir",
        default="models",
        help="Path to base models directory (default: models).",
    )
    parser.add_argument(
        "--task",
        choices=CORE_TASKS + ["all"],
        default=TASK_ARCHITECTURE,
        help="Review task type (syntax, security, architecture, auto_remediation, or all).",
    )
    parser.add_argument(
        "--bundle",
        help="Explicitly request model bundle (b01-b05). Must be authorized by license.",
    )
    parser.add_argument(
        "--license-token",
        help="License token string (overrides LICENSE_TOKEN env var / license.jwt file).",
    )
    parser.add_argument(
        "--license-path",
        help="Path to license token file (e.g. license.jwt).",
    )
    parser.add_argument(
        "--public-key-path",
        help="Path to RSA public key PEM file for validation.",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output report format (text or json).",
    )
    parser.add_argument(
        "--output-file",
        help="File path to save the generated report.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with non-zero code if critical infrastructure vulnerabilities are found.",
    )

    args = parser.parse_args()

    # 1. Cryptographic License Verification (Air-Gapped Offline RSA-4096)
    try:
        license_data = verify_license(
            token=args.license_token,
            token_path=Path(args.license_path) if args.license_path else None,
            public_key_path=Path(args.public_key_path) if args.public_key_path else None,
            required_bundle=args.bundle,
            required_task=args.task if args.task != "all" else None,
        )
    except LicenseMissingError as exc:
        sys.stderr.write(f"\n[LICENSE ERROR] {exc}\n")
        sys.stderr.write("Air-gapped operation requires a valid cryptographic license.\n")
        sys.exit(1)
    except (LicenseExpiredError, LicenseInvalidError, BundleNotAuthorizedError) as exc:
        sys.stderr.write(f"\n[LICENSE VERIFICATION FAILED] {exc}\n")
        sys.exit(1)
    except Exception as exc:
        sys.stderr.write(f"\n[UNEXPECTED LICENSING ERROR] {exc}\n")
        sys.exit(1)

    # 2. Model Bundle Resolution
    if args.bundle:
        active_bundle = args.bundle.lower().strip()
    else:
        active_bundle = get_bundle_for_task(
            payload=license_data,
            task=args.task if args.task != "all" else TASK_ARCHITECTURE,
            fallback_bundle="b04",
        )

    model_dir = resolve_model_directory(active_bundle, Path(args.model_dir).resolve())
    bundle_meta = MODEL_BUNDLES.get(active_bundle, {})

    # 3. Execute Infrastructure Reviewer
    try:
        from scripts.infrastructure_reviewer import review as run_infra_review

        repo_root = Path(args.repo_path).resolve()
        review_result = run_infra_review(
            repo_root=repo_root,
            model_metadata={
                "bundle_id": active_bundle,
                "model_name": bundle_meta.get("name", active_bundle),
                "model_dir": str(model_dir),
            },
        )
    except Exception as exc:
        sys.stderr.write(f"[ERROR] Reviewer execution failed: {exc}\n")
        sys.exit(1)

    # 4. Optional SaaS Telemetry (Never blocks on failure)
    customer_id = license_data.get("sub", "unknown")
    report_telemetry_event(
        customer_id=customer_id,
        event_type="review_completed",
        bundle_id=active_bundle,
        task_type=args.task,
        metrics={
            "score": review_result["score"],
            "grade": review_result["grade"],
            "files_scanned": review_result["files_scanned"],
            "total_findings": review_result["total_findings"],
        },
    )

    # 5. Output Report
    if args.output_format == "json":
        output_str = json.dumps(
            {
                "license": {
                    "customer": customer_id,
                    "tier": license_data.get("tier"),
                    "plan": license_data.get("plan"),
                    "offline_air_gapped": license_data.get("offline_air_gapped", True),
                },
                "bundle": active_bundle,
                "task": args.task,
                "review": review_result,
            },
            indent=2,
        )
    else:
        output_str = format_report_text(
            license_data=license_data,
            bundle_id=active_bundle,
            task=args.task,
            review_result=review_result,
        )

    print(output_str)

    if args.output_file:
        Path(args.output_file).write_text(output_str, encoding="utf-8")
        print(f"\nReport saved to: {args.output_file}")

    # Check for critical failures if requested
    if args.fail_on_critical and review_result["severity_summary"]["critical"] > 0:
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
