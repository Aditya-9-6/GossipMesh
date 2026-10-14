# Security Policy

## Supported Versions

We support the latest version of GossipMesh. Security updates will be applied to the primary `main` branch.

## Reporting a Vulnerability

Please do not open a public issue on GitHub for security vulnerabilities.
Instead, send an email to the repository maintainers with the details of the issue.
You should receive a response within 48 hours acknowledging receipt of the vulnerability.

## Secret Handling Practices

*   **No Default Secrets:** Sensitive values like database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`), secret keys (`SECRET_KEY`), and encryption keys (`ENCRYPTION_KEY`) must **not** have default values in the codebase.
*   **Environment Variables:** All configuration secrets and connection strings must be provided via environment variables.

## AI Security Directives

*   AI agents must never receive unrestricted production credentials.
*   AI agents must not push or merge without explicit policy authorization.
*   AI agents must not write arbitrary files directly; all patches must go through a validation pipeline.

## General Security Guidelines

*   For path validation in Python, prefer using `os.path.commonpath` instead of `str.startswith()` to prevent traversal vulnerabilities.
*   To prevent command injection vulnerabilities, system commands executed via `run_cmd`, `subprocess.run`, or `subprocess.Popen` must avoid `shell=True` and use argument lists instead of interpolated f-strings. If accepting string commands, parse them safely using `shlex.split()` before execution.
