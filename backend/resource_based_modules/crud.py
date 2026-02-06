from __future__ import annotations

from typing import Any, Iterable, Type, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


def get_by_id(*, db_session: Session, model: Type[ModelT], id: Any) -> ModelT | None:
    """Get a row by primary key."""
    return db_session.get(model, id)


def get_one_by(
    *, db_session: Session, model: Type[ModelT], **filters: Any
) -> ModelT | None:
    """Get a single row by equality filters (one_or_none)."""
    return db_session.query(model).filter_by(**filters).one_or_none()


def get_many_by(
    *, db_session: Session, model: Type[ModelT], **filters: Any
) -> list[ModelT]:
    """Get many rows by equality filters (all)."""
    return db_session.query(model).filter_by(**filters).all()


def get_all(*, db_session: Session, model: Type[ModelT]):
    """Return a Query for all rows (Dispatch-style, chainable)."""
    return db_session.query(model)


def create(
    *,
    db_session: Session,
    obj: ModelT,
    commit: bool = True,
) -> ModelT:
    """
    Persist a new ORM object.

    Accepts only an ORM model instance (not a schema).
    Object construction and validation are expected to be handled by the caller.
    """
    db_session.add(obj)

    if commit:
        db_session.commit()
        db_session.refresh(obj)

    return obj


def get_or_create(
    *,
    db_session: Session,
    model: Type[ModelT],
    lookup: dict[str, Any],
    obj: ModelT,
    commit: bool = True,
) -> ModelT:
    """
    Get a row by `lookup` filters, otherwise persist the provided ORM object.

    If a matching row exists, it is returned and `obj` is not persisted.
    """
    existing = db_session.query(model).filter_by(**lookup).one_or_none()
    if existing is not None:
        return existing

    return create(db_session=db_session, obj=obj, commit=commit)


def update(
    *,
    db_session: Session,
    db_obj: ModelT,
    update_fields: Iterable[str] | None = None,
    commit: bool = True,
) -> ModelT:
    """
    Persist changes to an existing ORM object.

    `update_fields` behaves like Django's `update_fields`:
    - If provided, only validates that the listed attributes exist on the object.
    - Actual field assignment must already be done by the caller.
    """
    if update_fields is not None:
        for field in update_fields:
            if not hasattr(db_obj, field):
                raise AttributeError(
                    f"{type(db_obj).__name__} has no attribute {field!r}"
                )

    if commit:
        db_session.commit()
        db_session.refresh(db_obj)

    return db_obj


def delete(
    *,
    db_session: Session,
    obj: ModelT,
    commit: bool = True,
) -> None:
    """
    Delete an existing ORM object instance.
    """
    db_session.delete(obj)
    if commit:
        db_session.commit()


def delete_by_id(
    *,
    db_session: Session,
    model: Type[ModelT],
    id: Any,
    commit: bool = True,
) -> None:
    """
    Delete a row by primary key (no-op if not found).
    """
    obj = db_session.get(model, id)
    if obj is None:
        return

    delete(db_session=db_session, obj=obj, commit=commit)
