from fastapi import Request, status
from fastapi.responses import JSONResponse
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


async def library_exception_handler(request: Request, exc: LibraryAppError):
    if isinstance(
        exc, (MemberNotFoundError, BookNotFoundError, BorrowRecordNotFoundError)
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )
    if isinstance(
        exc,
        (
            InventoryUnavailableError,
            BorrowLimitExceededError,
            AlreadyReturnedError,
            ActiveBorrowExistsError,
        ),
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )
    # Default for other library errors
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )
