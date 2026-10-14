# Contributing to GossipMesh

Thank you for your interest in contributing to GossipMesh!

## Getting Started

Please see `docs/DEVELOPMENT.md` for instructions on setting up your local environment.
The project requires Python version >= 3.10.

## Coding Standards

*   **Formatting:** Python code formatting is enforced using `black -l 100`.
*   **Linting:** We use `flake8 --max-line-length=100` for linting.
*   **Type Checking:** We plan to transition to using `mypy` for static type checking.
*   **Testing:** Unit tests are executed using: `python -m unittest discover -s tests -p "test_*.py" -v`. We plan to migrate to `pytest`.

## Commit Conventions

We follow specific commit title conventions to automatically categorize changes:

*   **Code Health Improvements:** Submit PRs with the title format `🧹 [description]`. The description should contain explicit 'What', 'Why', 'Verification', and 'Result' sections.
*   **Testing Improvements:** Submit PRs with the title format `🧪 [testing improvement description]`. The description should contain explicit 'What' (the testing gap addressed), 'Coverage' (scenarios newly tested), and 'Result' (improvement in test coverage) sections.
*   **Performance Improvements:** Submit PRs with the title format `⚡ [performance improvement description]`. The description should contain explicit 'What', 'Why', and 'Measured Improvement' sections.

For general features and bug fixes, standard commit messages are acceptable but please provide clear descriptions in your PR.

## Security Practices

*   Sensitive values like database credentials **must not** have default values in the codebase. Always enforce their secure provision via environment variables.
*   Please review `SECURITY.md` for full security guidelines before submitting changes.
