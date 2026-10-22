"""
CycloneDX Software Bill of Materials (SBOM) Generator (Task 105).

Generates standard CycloneDX JSON SBOM for GossipMesh dependencies and components.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path
from typing import Any, Dict, List


def generate_sbom(workspace_dir: Path | str = ".") -> Dict[str, Any]:
    """Generates a CycloneDX 1.5 JSON SBOM for Python dependencies."""
    components: List[Dict[str, Any]] = []

    for dist in distributions():
        name = dist.metadata.get("Name")
        version = dist.metadata.get("Version")
        license_name = dist.metadata.get("License") or "Unknown"

        if not name or not version:
            continue

        purl = f"pkg:pypi/{name.lower()}@{version}"
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": purl,
                "licenses": [{"license": {"name": license_name}}],
            }
        )

    # Sort deterministically
    components.sort(key=lambda c: c["name"].lower())

    sbom = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:gossipmesh-sbom-{int(datetime.now(timezone.utc).timestamp())}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "type": "application",
                "name": "gossipmesh",
                "version": "0.1.0",
                "description": "Enterprise Autonomous AI Code Review Mesh",
            },
        },
        "components": components,
    }
    return sbom


def main():
    sbom = generate_sbom()
    out_path = Path("sbom.json")
    out_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    print(f"[+] Successfully generated CycloneDX SBOM at {out_path} ({len(sbom['components'])} components)")


if __name__ == "__main__":
    main()
