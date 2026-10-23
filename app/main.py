"""FastAPI application entry point."""

from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.comments import models as _comment_models
from app.comments.router import close_pii_detector, router as comments_router
from app.database import Base, SessionLocal, _enable_sqlite_foreign_keys, get_db
from app.errors import APIError, api_error_handler
from app.users import models as _user_models


def create_app(session_factory: sessionmaker[Session] = SessionLocal) -> FastAPI:
    """Create the API application with an injectable database session factory."""
    bind = session_factory.kw["bind"]
    _enable_sqlite_foreign_keys(bind)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Generator[None, None, None]:
        migration_config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        with bind.begin() as connection:
            migration_config.attributes["connection"] = connection
            command.upgrade(migration_config, "head")
        try:
            yield
        finally:
            close_pii_detector()

    application = FastAPI(title="Comments API", lifespan=lifespan)
    application.add_exception_handler(APIError, api_error_handler)

    def get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = get_session
    application.include_router(comments_router)
    return application


app = create_app()