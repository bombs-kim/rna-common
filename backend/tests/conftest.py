"""Pytest configuration: test DB and fixtures for HTTP tests."""

import os
from pathlib import Path

import pytest

# Set env before any app/settings import so the app uses test DB and optional dummy keys.
_TEST_DB = Path(__file__).resolve().parent / "test_db.sqlite3"
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_TEST_DB}"
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("CURSOR_API_KEY", "test-cursor-key")


@pytest.fixture(scope="session", autouse=True)
def create_db_tables():
    """Create DB tables once per test session (after app/engine are loaded)."""
    from resource_based_modules.database.core import Base, engine
    from resource_based_modules.project.models import (
        Project,
    )  # noqa: F401 - register with Base

    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db_session():
    """Session for test data setup; commits so request-scoped middleware sees it."""
    from resource_based_modules.database.core import SessionLocal

    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clear_projects(db_session):
    """Clear project table before each test so tests start with empty projects."""
    from resource_based_modules.project.models import Project

    db_session.query(Project).delete()
    db_session.commit()
    yield
