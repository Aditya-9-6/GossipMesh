# GossipMesh Development Guide

## Prerequisites

*   **Python:** version >= 3.10
*   **PostgreSQL:** Required for database operations.
*   **Redis:** Required for background workers (Celery).

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Aditya-9-6/GossipMesh.git
    cd GossipMesh
    ```

2.  **Set up a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -e .[api]
    ```

## Environment Variables

For security reasons, sensitive values do not have defaults in the codebase.
You must export the following environment variables, especially when testing:

```bash
export POSTGRES_USER=your_user
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=your_db
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export SECRET_KEY=your_secret_key
export ENCRYPTION_KEY=your_encryption_key
```

When testing webhooks locally or in CI without signatures, mock `os.environ["ENVIRONMENT"] = "development"` to bypass strict signature verification.

## Running Tests

Unit tests are currently executed using `unittest`.
To run tests locally, assure environment variables are set and execute:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

> Note: We plan to migrate to `pytest` in the future.

## Code Quality

Before committing, please ensure your code follows the established standards:
*   Format your code using `black -l 100`
*   Lint your code using `flake8 --max-line-length=100`

We recommend installing `pre-commit` hooks:
```bash
pip install pre-commit
pre-commit install
```
