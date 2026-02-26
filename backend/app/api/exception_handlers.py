from typing import Optional, List
from fastapi import Request, status
from fastapi.responses import JSONResponse
import traceback
from app.core.logging import logger
from app.core.exceptions import (
    LibraryAppError,
    InventoryUnavailableError,
    BorrowLimitExceededError,
    AlreadyReturnedError,
    MemberNotFoundError,
    BookNotFoundError,
    BorrowRecordNotFoundError,
    ActiveBorrowExistsError,
)
import uuid
from fastapi.exceptions import RequestValidationError
from app.core.logging import correlation_id_ctx



def _create_error_response(
    request: Request,
    status_code: int,
    detail: str,
    error_code: str = "INTERNAL_ERROR",
    validation_errors: Optional[list] = None,
) -> JSONResponse:
    """Helper to create standardized error responses."""
    # Try context first, then request headers, finally generate new if all else fails
    corr_id = correlation_id_ctx.get() or request.headers.get("X-Correlation-ID")
    if not corr_id:
        corr_id = str(uuid.uuid4())
        
    content = {
        "detail": detail,
        "error_code": error_code,
        "correlation_id": corr_id,
    }
    if validation_errors:
        content["validation_errors"] = validation_errors
    return JSONResponse(status_code=status_code, content=content)


async def library_exception_handler(request: Request, exc: LibraryAppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "LIBRARY_ERROR"

    if isinstance(exc, MemberNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_code = "MEMBER_NOT_FOUND"
    elif isinstance(exc, BookNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_code = "BOOK_NOT_FOUND"
    elif isinstance(exc, BorrowRecordNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_code = "BORROW_RECORD_NOT_FOUND"
    elif isinstance(exc, InventoryUnavailableError):
        status_code = status.HTTP_409_CONFLICT
        error_code = "INVENTORY_UNAVAILABLE"
    elif isinstance(exc, BorrowLimitExceededError):
        status_code = status.HTTP_409_CONFLICT
        error_code = "BORROW_LIMIT_EXCEEDED"
    elif isinstance(exc, AlreadyReturnedError):
        status_code = status.HTTP_409_CONFLICT
        error_code = "ALREADY_RETURNED"
    elif isinstance(exc, ActiveBorrowExistsError):
        status_code = status.HTTP_409_CONFLICT
        error_code = "ACTIVE_BORROW_EXISTS"

    return _create_error_response(
        request=request, status_code=status_code, detail=str(exc), error_code=error_code
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Specific handler for FastAPI/Pydantic validation errors."""
    return _create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Input validation failed",
        error_code="VALIDATION_ERROR",
        validation_errors=exc.errors(),
    )


async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for any unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())

    return _create_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again later.",
        error_code="INTERNAL_SERVER_ERROR",
    )
