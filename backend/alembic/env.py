import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. Import Base and Settings
from app.core.config import settings
from app.common.entity.base import Base
# Import all models to ensure they are registered
from app.modules.iam import models as iam_models  # noqa
from app.modules.notification import models as notification_models  # noqa
from app.modules.audit.models import audit_log as audit_models  # noqa
from app.modules.schedule import models as schedule_models  # noqa
from app.modules.preservation.models import detection as preservation_models  # noqa
from app.modules.collection.models import sip as collection_models  # noqa
from app.modules.repository.models import archive as repository_models  # noqa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Set sqlalchemy.url from Pydantic settings
# Note: Escape % signs if necessary, but usually raw URL is fine here
# We need to ensure the driver is asyncpg
db_url = settings.SQLALCHEMY_DATABASE_URI
config.set_main_option("sqlalchemy.url", db_url)

# 3. Set target_metadata
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())