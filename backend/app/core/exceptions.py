class LibraryAppError(Exception):
    """Base exception for the library application."""

    pass


class InventoryUnavailableError(LibraryAppError):
    """Raised when a book is not available for borrowing."""

    pass


class BorrowLimitExceededError(LibraryAppError):
    """Raised when a member has reached the maximum number of active borrows."""

    pass


class AlreadyReturnedError(LibraryAppError):
    """Raised when attempting to return a book that is already returned."""

    pass


class MemberNotFoundError(LibraryAppError):
    """Raised when a member is not found."""

    pass


class BookNotFoundError(LibraryAppError):
    """Raised when a book is not found."""

    pass


class BorrowRecordNotFoundError(LibraryAppError):
    """Raised when a borrow record is not found."""

    pass


class ActiveBorrowExistsError(LibraryAppError):
    """Raised when a member already has an active borrow for a book."""

    pass
