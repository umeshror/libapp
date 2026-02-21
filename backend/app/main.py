"""Application factory for the Neighborhood Library Service."""

import time
import uuid
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.shared.deps import get_db
from app.api.v1 import v1_router
from app.core.exceptions import LibraryAppError
from app.api.exception_handlers import library_exception_handler
from app.core.logging import logger, correlation_id_ctx
from app.core.metrics import metrics
from fastapi.middleware.cors import CORSMiddleware
from app.core.security import rate_limit_dependency


def get_application() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="Neighborhood Library Service",
        description="API for managing books, members, and borrows.",
        version="1.0.0",
    )

    # Middleware: CORS
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

    # Middleware: Correlation ID & Logging
    @application.middleware("http")
    async def request_middleware(request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        token = correlation_id_ctx.set(corr_id)

        start_time = time.time()
        logger.info(f"Started {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            response.headers["X-Correlation-ID"] = corr_id

            logger.info(
                f"Completed {request.method} {request.url.path} Status: {response.status_code} Duration: {process_time:.4f}s"
            )
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise e
        finally:
            correlation_id_ctx.reset(token)

    # Versioned API routes
    application.include_router(v1_router, prefix="/api/v1")

    # Register Exception Handlers
    application.add_exception_handler(LibraryAppError, library_exception_handler)  # type: ignore

    # Infrastructure endpoints (un-versioned)
    @application.get("/health")
    def health_check(db: Session = Depends(get_db)):
        """Database connectivity health check."""
        try:
            db.execute(text("SELECT 1"))
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
