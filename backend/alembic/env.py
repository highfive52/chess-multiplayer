import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import MetaData, engine_from_config, pool

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This project uses hand-written migrations, so no ORM metadata is required
# for Alembic autogeneration.
target_metadata = MetaData()

# 2. Override sqlalchemy.url with DATABASE_URL if set in environment
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Handle legacy Heroku/Render dialect prefix
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Force SQLAlchemy to use 'psycopg' (v3) instead of defaulting to missing 'psycopg2'
    if (
        database_url.startswith("postgresql://")
        and "+" not in database_url.split("://")[0]
    ):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
