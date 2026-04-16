"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import init_db, close_db, get_settings
from etl.router import router as etl_router
from ml.router import router as ml_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting FinUp Price Tracker API")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down FinUp Price Tracker API")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="FinUp Price Tracker",
    description="Cryptocurrency price monitoring with ML anomaly detection and RAG-powered explanations",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["https://finup.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
async def root():
    """Welcome endpoint."""
    return {
        "message": "FinUp Price Tracker API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FinUp Price Tracker",
        "environment": settings.environment,
    }


@app.get("/status", tags=["health"])
async def status_check():
    """Detailed status check."""
    return {
        "status": "ok",
        "service": "FinUp Price Tracker API",
        "version": "0.1.0",
        "environment": settings.environment,
        "database": settings.database_url.split("@")[0] + "@...",
        "coingecko_enabled": True,
    }


# Register routers
app.include_router(etl_router)
app.include_router(ml_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )
