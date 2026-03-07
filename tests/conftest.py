"""
Test configuration and fixtures for FIE v3.

Sets up an in-memory SQLite database and a FastAPI test client
so tests run in isolation without touching production data.
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Override DATABASE_URL before any app code imports it
# SQLite in-memory won't work across threads, so use a temp file
os.environ["DATABASE_URL"] = "sqlite:///test_fie.db"
# Prevent the server startup from launching background threads
os.environ["FIE_TESTING"] = "1"

from models import Base, get_db  # noqa: E402
from server import app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine that lives for the entire test session."""
    test_engine = create_engine(
        "sqlite:///test_fie.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("test_fie.db"):
        os.remove("test_fie.db")


@pytest.fixture
def db_session(engine):
    """Create a fresh database session for each test.

    Cleans all table data before each test to ensure full isolation,
    since the server startup can seed data via background threads
    that bypass the test session.
    """
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = TestSessionLocal()

    # Clean all tables before each test for isolation
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
    """
    Create a test FastAPI client with database dependency override.

    Patches the server startup background thread to prevent yfinance
    backfill from polluting the test database.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Suppress background threads that the startup event fires
    with patch("server.threading.Thread") as mock_thread:
        mock_thread.return_value.start = lambda: None
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()
