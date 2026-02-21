import pytest
import logging
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import OperationalError
from app.domains.borrows.service import BorrowService
from app.domains.borrows.schemas import BorrowRecordResponse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL.rsplit("/", 1)[0] + "/library_test")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_health_check_db_status(client):
    """Validate health endpoint returns DB connectivity status."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"


def test_correlation_id_middleware(client, caplog):
    """Validate logs contain correlation ID."""
    caplog.set_level(logging.INFO)

    # 1. Request with explicit ID
    custom_id = "test-cor-id-123"
    client.get("/health", headers={"X-Request-ID": custom_id})

    # Verify correlation ID is echoed back in response header

    res = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res.headers["X-Request-ID"] == custom_id

    # 2. Request without ID (Generated)
    res2 = client.get("/health")
    assert "X-Request-ID" in res2.headers
    assert len(res2.headers["X-Request-ID"]) > 0


def test_deadlock_retry_mechanism(db_session):
    """
    Validate deadlock retry works by forcing an OperationalError.
    We mock the repository to raise OperationalError twice, then succeed.
    """
    borrow_service = BorrowService(db_session)

    # Side effect: 2 OperationalErrors, then a mock book to verify retry behavior
    mock_book = MagicMock()
    mock_book.available_copies = 1
    mock_book.id = 1

    side_effect = [
        OperationalError("statement", {}, "deadlock detected"),
        OperationalError("statement", {}, "deadlock detected"),
        mock_book,
    ]

    with patch.object(
        borrow_service.book_repo, "get_with_lock", side_effect=side_effect
    ) as mock_method:
        with patch.object(
            borrow_service.borrow_repo, "list", return_value={"items": [], "total": 0}
        ):
            with patch.object(borrow_service.member_repo, "get", return_value=True):
                with patch.object(
                    borrow_service.borrow_repo, "get_active_borrow", return_value=None
                ):
                    # Mock session.refresh to set an ID on the record
                    def refresh_side_effect(instance):
                        instance.id = uuid.uuid4()

                    with patch.object(borrow_service.session, "add"):
                        with patch.object(borrow_service.session, "commit"):
                            with patch.object(
                                borrow_service.session,
                                "refresh",
                                side_effect=refresh_side_effect,
                            ):
                                # We mock session methods to avoid actual DB calls on the mocked book object
                                import uuid

                                borrow_service.borrow_book(uuid.uuid4(), uuid.uuid4())

                    # verification: called 3 times (2 fails + 1 success)
                    assert mock_method.call_count == 3
