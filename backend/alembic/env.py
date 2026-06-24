"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import get_settings
from app.core.database import Base

# Import all models so they are registered with Base.metadata
from app.models.user import User
from app.models.target import Target
from app.models.scan import Scan
from app.models.legal import NDAAcceptance, AuditLog
from app.models.notification import Notification
from app.models.scheduled_scan import ScheduledScan
from app.models.credits import ScanCredit, CreditUsage

config = context.config
settings = get_settings()

# Use sync URL for alembic config (psycopg2) and async URL for the runtime engine
SYNC_URL = settings.database_url_sync  # postgresql://...
ASYNC_URL = settings.database_url       # postgresql+asyncpg://...

config.set_main_option("sqlalchemy.url", SYNC_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Use the asyncpg URL for the async engine
    connectable = async_engine_from_config(
        {**config.get_section(config.config_ini_section, {}),
         "sqlalchemy.url": ASYNC_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
