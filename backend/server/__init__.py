import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from resource_based_modules.database.core import SessionLocal
from resource_based_modules.database.logging import SessionTracker
from server.http import router as http_router
from server.ws import router as ws_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Steps Backend")


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """Create a request-scoped DB session; set request.state.db; commit/rollback and close after request."""
    session = SessionLocal()
    request.state.db = session
    request.state.db._session_id = SessionTracker.track_session(
        request.state.db, context="fastapi_request"
    )
    try:
        response = await call_next(request)
        if hasattr(request.state, "db") and request.state.db.is_active:
            request.state.db.commit()
        return response
    except Exception:
        if hasattr(request.state, "db") and request.state.db.is_active:
            try:
                request.state.db.rollback()
            except Exception as rollback_error:
                logging.error("Error during rollback: %s", rollback_error)
        raise
    finally:
        if hasattr(request.state, "db"):
            if hasattr(request.state.db, "_session_id"):
                try:
                    SessionTracker.untrack_session(request.state.db._session_id)
                except Exception as untrack_error:
                    logging.error("Failed to untrack session: %s", untrack_error)
            try:
                request.state.db.close()
            except Exception as close_error:
                logging.error("Error closing database session: %s", close_error)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(http_router)
app.include_router(ws_router)
