"""Database engine, session, and declarative base for resource_based_modules."""

import functools
import re
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm import DeclarativeBase, declared_attr
from starlette.requests import Request

from settings import settings

from resource_based_modules.database.logging import SessionTracker


def create_db_engine(connection_string: str):
    """Create a database engine with pool settings from config."""
    url = make_url(connection_string)
    pool_kwargs = {
        "pool_timeout": settings.DATABASE_ENGINE_POOL_TIMEOUT,
        "pool_recycle": settings.DATABASE_ENGINE_POOL_RECYCLE,
        "pool_size": settings.DATABASE_ENGINE_POOL_SIZE,
        "max_overflow": settings.DATABASE_ENGINE_MAX_OVERFLOW,
        "pool_pre_ping": settings.DATABASE_ENGINE_POOL_PING,
    }
    return create_engine(url, **pool_kwargs)


engine = create_db_engine(settings.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def resolve_table_name(name: str) -> str:
    """Resolve class name to table name (CamelCase -> snake_case)."""
    parts = re.split("(?=[A-Z])", name)
    return "_".join(p.lower() for p in parts if p)


def resolve_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Access attr via dotted notation; return default if missing."""
    try:
        return functools.reduce(getattr, attr.split("."), obj)
    except AttributeError:
        return default


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    __repr_attrs__: list[str] = []
    __repr_max_length__: int = 15

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return resolve_table_name(cls.__name__)

    def dict(self) -> dict[str, Any]:
        """Return a dict of column names to values."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @property
    def _id_str(self) -> str:
        ids = inspect(self).identity
        if ids:
            return "-".join(str(x) for x in ids) if len(ids) > 1 else str(ids[0])
        return "None"

    @property
    def _repr_attrs_str(self) -> str:
        max_length = self.__repr_max_length__
        values = []
        single = len(self.__repr_attrs__) == 1
        for key in self.__repr_attrs__:
            if not hasattr(self, key):
                raise KeyError(
                    f"{self.__class__!r} has incorrect attribute {key!r} in __repr_attrs__"
                )
            value = getattr(self, key)
            wrap = isinstance(value, str)
            value = str(value)
            if len(value) > max_length:
                value = value[:max_length] + "..."
            if wrap:
                value = f"'{value}'"
            values.append(value if single else f"{key}:{value}")
        return " ".join(values)

    def __repr__(self) -> str:
        id_str = ("#" + self._id_str) if self._id_str else ""
        repr_str = " " + self._repr_attrs_str if self._repr_attrs_str else ""
        return f"<{self.__class__.__name__} {id_str}{repr_str}>"


def get_db(request: Request) -> Session:
    """Return the request-scoped database session (set by middleware)."""
    session = request.state.db
    assert hasattr(
        session, "_session_id"
    ), "Session must be created by db_session_middleware"
    return session


DbSession = Annotated[Session, Depends(get_db)]


@contextmanager
def get_session():
    """Context manager: create session, commit on success, rollback on error, then close."""
    session = SessionLocal()
    session_id = SessionTracker.track_session(session, context="context_manager")
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        SessionTracker.untrack_session(session_id)
        session.close()
