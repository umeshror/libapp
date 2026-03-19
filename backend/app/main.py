"""Application factory for the Neighborhood Library Service."""

import time
import uuid
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.shared.deps import get_uow
from app.api.v1 import v1_router
from app.core.exceptions import LibraryAppError
from app.api.exception_handlers import library_exception_handler
from app.core.logging import logger
from app.core.metrics import metrics
from fastapi.middleware.cors import CORSMiddleware
from app.core.security import rate_limit_dependency
from app.core.middleware.monitoring import MonitoringMiddleware
from app.shared.uow import UnitOfWork


def get_application() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="Neighborhood Library Service",
        description="API for managing books, members, and borrows.",
        version="1.0.0",
    )


    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3003",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3003",
            "http://0.0.0.0:3000",
            "http://0.0.0.0:3003",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    application.add_middleware(MonitoringMiddleware)

    # Versioned API routes
    application.include_router(v1_router, prefix="/api/v1")

    # Register Exception Handlers
    from app.api.exception_handlers import global_exception_handler, validation_exception_handler
    from fastapi.exceptions import RequestValidationError
    application.add_exception_handler(LibraryAppError, library_exception_handler)  # type: ignore
    application.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
    application.add_exception_handler(Exception, global_exception_handler)


    @application.get("/health")
    def health_check(uow: UnitOfWork = Depends(get_uow)):
        """Database connectivity health check."""
        try:
            uow.session.execute(text("SELECT 1"))
            return {"status": "ok", "db": "connected"}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={"status": "error", "detail": "Database unavailable"},
            )

    @application.get("/metrics")
    def get_metrics():
        """Return in-memory application metrics."""
        return metrics.get_stats()

    return application


app = get_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
