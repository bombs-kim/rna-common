"""Interactive shell with CRUD bound to a session. Run from backend: uv run python shell.py."""

import code
from types import SimpleNamespace

from resource_based_modules import crud
from resource_based_modules.database.core import Base, engine, SessionLocal
from resource_based_modules.project.models import Project


def bind_crud(session):
    """Return CRUD helpers with session bound (one step)."""

    def get_by_id(model, id):
        return crud.get_by_id(db_session=session, model=model, id=id)

    def get_one_by(model, **filters):
        return crud.get_one_by(db_session=session, model=model, **filters)

    def get_many_by(model, **filters):
        return crud.get_many_by(db_session=session, model=model, **filters)

    def get_all(model):
        return crud.get_all(db_session=session, model=model)

    def create(obj, *, commit=True):
        return crud.create(db_session=session, obj=obj, commit=commit)

    def get_or_create(model, lookup, obj, *, commit=True):
        return crud.get_or_create(
            db_session=session, model=model, lookup=lookup, obj=obj, commit=commit
        )

    def update(db_obj, *, update_fields=None, commit=True):
        return crud.update(
            db_session=session,
            db_obj=db_obj,
            update_fields=update_fields,
            commit=commit,
        )

    def delete(obj, *, commit=True):
        return crud.delete(db_session=session, obj=obj, commit=commit)

    def delete_by_id(model, id, *, commit=True):
        return crud.delete_by_id(db_session=session, model=model, id=id, commit=commit)

    return SimpleNamespace(
        get_by_id=get_by_id,
        get_one_by=get_one_by,
        get_many_by=get_many_by,
        get_all=get_all,
        create=create,
        get_or_create=get_or_create,
        update=update,
        delete=delete,
        delete_by_id=delete_by_id,
    )


session = SessionLocal()
db = bind_crud(session)

_banner = (
    "CRUD: get_by_id, get_one_by, get_many_by, get_all, create, get_or_create, update, delete, delete_by_id\n"
    "e.g.  projects   or   get_all(Project).all()   or   get_by_id(Project, 1)"
)
_locals = {
    "Project": Project,
    "get_by_id": db.get_by_id,
    "get_one_by": db.get_one_by,
    "get_many_by": db.get_many_by,
    "get_all": db.get_all,
    "create": db.create,
    "get_or_create": db.get_or_create,
    "update": db.update,
    "delete": db.delete,
    "delete_by_id": db.delete_by_id,
    "Base": Base,
    "engine": engine,
}
try:
    code.interact(local=_locals, banner=_banner)
finally:
    session.close()
