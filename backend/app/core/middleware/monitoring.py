import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from app.core.logging import logger, correlation_id_ctx


class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_ctx.set(correlation_id)
        
        response = await call_next(request)
        
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Correlation-ID"] = correlation_id
        
        logger.info(
            f"Method: {request.method} Path: {request.url.path} "
            f"Status: {response.status_code} Latency: {process_time:.4f}s"
        )
        
        return response
