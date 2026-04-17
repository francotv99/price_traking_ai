"""Dependency injection for FastAPI."""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from api.settings import Settings

logger = logging.getLogger(__name__)

# Global settings instance
_settings: Settings | None = None

# Database engine and session factory
_engine = None
_async_session_maker = None


def get_settings() -> Settings:
    """Get application settings (singleton).
    
    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


async def init_db() -> None:
    """Initialize database connection and session factory.
    
    Call this once during application startup.
    """
    global _engine, _async_session_maker

    settings = get_settings()

    # Convert standard postgresql:// URL to async psycopg3
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

    logger.info(f"Initializing database connection: {settings.database_url.split('@')[0]}@...")

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

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close database connection.
    
    Call this once during application shutdown.
    """
    global _engine

    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection.
    
    Yields:
        AsyncSession for database operations
        
    Raises:
        RuntimeError: If database not initialized
    """
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
