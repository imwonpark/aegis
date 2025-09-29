import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import router
from .api.admin import admin_router
from .core.dependencies import get_config, cleanup_services
from .core import middleware


# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """app lifecycle"""
    logger.info("Starting Aegis Guardrail service...")

    # startup
    yield

    # shutdown
    logger.info("Shutting down Aegis Guardrail service...")
    await cleanup_services()


def create_app() -> FastAPI:
    """create app"""
    config = get_config()

    app = FastAPI(
        title="Aegis Guardrail",
        description="Universal real-time policy enforcement and observability middleware",
        version="1.0.0",
        lifespan=lifespan
    )

    # cors middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # custom middleware
    app.middleware("http")(middleware.log_requests)
    app.middleware("http")(middleware.add_security_headers)

    # include routers
    app.include_router(router, prefix="/api")
    app.include_router(admin_router, prefix="/admin", tags=["admin"])

    # error handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)}
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level=config.log_config.level.lower()
    )
