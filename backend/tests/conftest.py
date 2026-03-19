import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Base
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from app.shared.deps import get_uow
from app.shared.uow import UnitOfWork
from app.core.config import settings

@pytest.fixture(scope="module")
def shared_engine():
    """Create a single engine for the module to ensure shared DB."""
    # Build test URI by replacing the DB name
    base_uri = settings.DATABASE_URL
    test_uri = base_uri.rsplit("/", 1)[0] + "/library_test"
    
    engine = create_engine(test_uri, poolclass=NullPool)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="module")
def session_factory(shared_engine):
    """Return a session factory bound to the shared engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=shared_engine)


@pytest.fixture(scope="module")
def db_session(session_factory):
    """Yield a session for test setup use."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def clean_db(session_factory):
    """Clean all tables before a test using a session to avoid deadlocks."""
    with session_factory() as session:
        try:
            session.execute(text("DELETE FROM auditlog;"))
            session.execute(text("DELETE FROM borrow_record;"))
            session.execute(text("DELETE FROM book;"))
            session.execute(text("DELETE FROM member;"))
            session.commit()
        except Exception:
            session.rollback()
            raise


@pytest.fixture(scope="function")
def uow(session_factory, clean_db):
    """Yield a UnitOfWork for test use with function scope, ensures clean DB."""
    uow = UnitOfWork(session_factory=session_factory)
    with uow:
        yield uow


@pytest.fixture(scope="function")
def client(session_factory, clean_db):
    """Yield a test client that uses a UnitOfWork bound to the test session factory, ensures clean DB."""

    def override_get_uow():
        uow = UnitOfWork(session_factory=session_factory)
        with uow:
            yield uow

    app.dependency_overrides[get_uow] = override_get_uow
    with TestClient(app) as c:
        yield c
