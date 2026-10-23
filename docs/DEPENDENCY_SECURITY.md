# GossipMesh Dependency Security & Vulnerability Policy (Task 105)

## 1. Overview
GossipMesh incorporates continuous dependency security scanning, automated Software Bill of Materials (SBOM) generation, and risk acceptance protocols across all software components and container bases.

## 2. Automated Vulnerability Scanning & Tooling
- **CI Scanning:** Every pull request runs automated dependency vulnerability scanning via `pip-audit`, `trivy`, and GitHub Dependabot.
- **Scheduled Scans:** Nightly scans analyze the full dependency graph and base container images against the National Vulnerability Database (NVD) and GitHub Advisory Database.

## 3. Vulnerability Remediation SLAs

| Severity | CVSS Score | Remediation SLA | Escalation Target |
|---|---|---|---|
| **CRITICAL** | `9.0 – 10.0` | **24 hours** | Immediate emergency patch / hotfix deployment |
| **HIGH** | `7.0 – 8.9` | **7 calendar days** | Expedited sprint release |
| **MEDIUM** | `4.0 – 6.9` | **30 calendar days** | Next scheduled minor release |
| **LOW** | `0.1 – 3.9` | **90 calendar days** | Regular dependency maintenance cycle |

## 4. Software Bill of Materials (SBOM)
- CycloneDX 1.5 JSON SBOMs are generated autonomously during release builds via `scripts/generate_sbom.py`.
- Includes library name, pinned version, package URL (`purl`), and license classification.

## 5. Risk Acceptance Policy
If a vulnerability cannot be immediately patched due to breaking upstream changes, a formal Risk Acceptance Form must be signed by the Security Administrator specifying:
1. Vulnerability CVE identifier and CVSS score.
2. Verified non-exploitability proof (e.g. affected code path is not invoked by GossipMesh runtime).
3. Compensating controls (e.g. strict rootless container sandbox, network egress filtering).
4. Mandatory expiration date (maximum 60 days).
