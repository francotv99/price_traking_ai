"""Dependency injection for FastAPI."""
from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.settings import Settings

logger = logging.getLogger(__name__)

_settings: Settings | None = None
_engine = None
_async_session_maker = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


async def init_db() -> None:
    global _engine, _async_session_maker

    settings = get_settings()
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

    logger.info("Initializing database connection: %s@...", settings.database_url.split("@")[0])

    _engine = create_async_engine(
        database_url,
        echo=settings.log_level == "DEBUG",
        pool_size=10,
        max_overflow=20,
    )
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("Database initialized")


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    global _async_session_maker
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
