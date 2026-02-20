import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.deps import get_db


@pytest.fixture(scope="module")
def shared_engine():
    """Create a single engine for the module to ensure shared in-memory DB."""
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


@pytest.fixture(scope="module")
def client(session_factory):
    """Yield a test client that uses the shared DB session."""

    def override_get_db():
        try:
            db = session_factory()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
