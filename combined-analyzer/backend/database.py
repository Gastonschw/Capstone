"""
Async SQLAlchemy database configuration.
"""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Apply the complete schema atomically before exposing application routes."""
    import models  # Register all models before create_all.

    migration_dir = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
    migrations = sorted(migration_dir.glob("*.sql"))
    async with engine.begin() as conn:
        await conn.execute(text("select pg_advisory_xact_lock(2710202601)"))
        await conn.execute(text(
            "create table if not exists public.application_schema_migrations "
            "(name text primary key, applied_at timestamptz not null default now())"
        ))
        applied = set((await conn.execute(text(
            "select name from public.application_schema_migrations"
        ))).scalars())
        raw = await conn.get_raw_connection()

        async def apply(migration):
            if migration.name not in applied:
                await raw.driver_connection.execute(migration.read_text(encoding="utf-8"))
                await conn.execute(
                    text("insert into public.application_schema_migrations(name) values (:name)"),
                    {"name": migration.name},
                )

        # Historical ownership migrations require both public.users and ORM tables.
        bootstrap = migration_dir / "20260216000000_create_public_users.sql"
        await apply(bootstrap)
        await conn.run_sync(Base.metadata.create_all)
        for migration in migrations:
            if migration != bootstrap:
                await apply(migration)
