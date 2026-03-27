"""Alembic migration environment configuration."""

import alembic.context
import sqlalchemy

import app.config as config
import app.database.models as database_models

target_metadata = database_models.Base.metadata

# Views managed via explicit op.execute() in migration scripts.
# Listing them here prevents autogenerate from treating them as missing tables
# and emitting spurious DROP statements when running db-revision.
_VIEWS = {"booking_timeline_view"}


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter out database views from Alembic autogenerate comparisons.

    Without this, autogenerate sees views as reflected tables that are not
    in the ORM metadata and generates DROP TABLE statements for them.

    :param object: the SQLAlchemy schema object being compared
    :param name: the object name
    :param type_: the object type string (e.g. ``"table"``)
    :param reflected: True if the object was reflected from the live DB
    :param compare_to: the corresponding object in the metadata, or None
    :return: False for known views, True for everything else
    """
    if type_ == "table" and name in _VIEWS:
        return False
    return True


def _get_url() -> str:
    """
    Resolve the database URL for migrations.

    Prefers the ``sqlalchemy.url`` key set in the Alembic config object
    (e.g. overridden programmatically in test fixtures via
    ``alembic_cfg.set_main_option("sqlalchemy.url", ...)``).
    Falls back to ``config.settings.database_url`` for normal CLI use.

    :return: SQLAlchemy connection URL string
    """
    return (
        alembic.context.config.get_main_option("sqlalchemy.url")
        or config.settings.database_url
    )


def run_migrations_offline() -> None:
    """
    Run migrations in offline mode (no live DB connection required).

    Emits SQL to stdout instead of executing against a live database.
    """
    alembic.context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in online mode (connects to the database and applies changes).
    """
    connectable = sqlalchemy.create_engine(_get_url())
    with connectable.connect() as connection:
        alembic.context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with alembic.context.begin_transaction():
            alembic.context.run_migrations()


if alembic.context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
