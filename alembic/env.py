"""Alembic migration environment configuration."""

import alembic.context
import sqlalchemy

import app.config as config
import app.database.models as database_models

target_metadata = database_models.Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in offline mode (no live DB connection required).

    Emits SQL to stdout instead of executing against a live database.
    """
    alembic.context.configure(
        url=config.settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in online mode (connects to the database and applies changes).
    """
    connectable = sqlalchemy.create_engine(config.settings.database_url)
    with connectable.connect() as connection:
        alembic.context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with alembic.context.begin_transaction():
            alembic.context.run_migrations()


if alembic.context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
