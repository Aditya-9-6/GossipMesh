import os
import sys
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from gossipmesh.core.config import settings
from gossipmesh.models.base import Base
from gossipmesh.models import user, organization, audit, provider

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    return str("sqlite:///gossipmesh.db")

def check_destructive_migrations():
    """Prevent destructive migrations (downgrades) in production."""
    if os.environ.get("ENVIRONMENT") == "production":
        # Check if this is a downgrade by checking the context
        if context.get_x_argument(as_dictionary=True).get("cmd") == "downgrade" or getattr(config.cmd_opts, "cmd", None) == "downgrade":
             raise RuntimeError("Downgrades are not allowed in the production environment.")

        # A more robust check by looking at the context's current migration context if available,
        # but in env.py we can check the command from context
        # alembic passes context.is_offline_mode(), etc.
        # But actually checking if it's a downgrade can be tricky, we can check sys.argv
        if "downgrade" in sys.argv:
            raise RuntimeError("Downgrades are not allowed in the production environment.")

def run_migrations_offline() -> None:
    url = get_url()
    check_destructive_migrations()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        check_destructive_migrations()
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
