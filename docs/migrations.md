# Database Migrations Workflow

GossipMesh uses [Alembic](https://alembic.sqlalchemy.org/en/latest/) for database migrations.

## Validating Migrations

A script is provided to validate that the current database schema matches the head of the migrations:
```bash
python scripts/validate_migrations.py
```
This is useful in deployment environments to ensure the application starts with a correct database schema.

## Tests

Upgrade and downgrade tests are implemented in `tests/test_migrations.py` to ensure migrations can be successfully applied and rolled back. These tests are executed automatically within the CI workflow using a temporary in-memory/local SQLite database.

```bash
python3 -m unittest tests/test_migrations.py
```

## Creating a new migration

To generate a new migration automatically from model changes:

```bash
alembic revision --autogenerate -m "Add new feature models"
```

## Startup Migration Policy & Destructive Migrations

**Important**: GossipMesh does not automatically run destructive migrations on startup.

- **Lifespan checks**: In `gossipmesh/api/main.py`, the FastAPI lifespan context verifies the current migration state before the app fully starts. If the database schema isn't up to date, it will log a warning or error to prevent runtime failures.
- **Production Downgrades**: Downgrades are strictly prevented in the `production` environment. The `alembic/env.py` script checks the `ENVIRONMENT` variable, and if it is set to `production`, any downgrade request will raise an exception to prevent accidental data loss.
