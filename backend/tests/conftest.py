import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.api.deps import get_db


from app.core.config import settings

@pytest.fixture(scope="module")
def shared_engine():
    """Create a single engine for the module to ensure shared DB."""
    # Build test URI by replacing the DB name
    base_uri = settings.DATABASE_URL
    test_uri = base_uri.rsplit("/", 1)[0] + "/library_test"
    
    engine = create_engine(test_uri)
    
    # Ensure clean state for the test module
    Base.metadata.drop_all(bind=engine)
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
