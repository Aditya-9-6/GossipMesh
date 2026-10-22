import json
from pathlib import Path
from scripts.generate_sbom import generate_sbom


def test_sbom_generation_format_and_components():
    sbom = generate_sbom()

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert "components" in sbom
    assert len(sbom["components"]) > 10

    comp_names = {c["name"].lower() for c in sbom["components"]}
    # Verify core framework packages are indexed
    assert "fastapi" in comp_names
    assert "sqlalchemy" in comp_names
    assert "pydantic" in comp_names
    assert "stripe" in comp_names

    # Check component structure
    sample = sbom["components"][0]
    assert "name" in sample
    assert "version" in sample
    assert "purl" in sample
    assert sample["purl"].startswith("pkg:pypi/")


def test_dependency_security_policy_slas():
    policy_path = Path("docs/DEPENDENCY_SECURITY.md")
    assert policy_path.is_file()

    content = policy_path.read_text(encoding="utf-8")
    assert "CRITICAL" in content
    assert "24 hours" in content
    assert "HIGH" in content
    assert "7 calendar days" in content
    assert "CycloneDX" in content
    assert "Risk Acceptance Policy" in content
