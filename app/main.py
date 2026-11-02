from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.comments.handler import CommentsHandler
from app.comments.repository import CommentRepository
from app.comments.service import CommentsService, ServiceConfig
from app.config.config import Config, setup
from app.db.database import Database, DatabaseConfig
from app.db.migrate import apply_migrations
from app.errors import APIError, api_error_handler
from app.util.azure.pii import AzurePiiDetector, NoopPiiDetector, PiiDetector
from app.util.token_validator import AuthConfig, TokenValidator

API_NAME = "Comments API"

def create_app(config: Config | None = None,database: Database | None = None,auth_config: AuthConfig | None = None) -> FastAPI:
    config = config or setup()
    database = database or Database(
        DatabaseConfig(url=config.db.url, echo=config.db.echo)
    )

    @lru_cache(maxsize=1)
    def get_pii_detector() -> AzurePiiDetector:
        if config.azure.pii_disabled:
            return NoopPiiDetector()
        
        return AzurePiiDetector(endpoint=config.azure.language_endpoint)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        if config.migrator.run:
            with database.engine.begin() as connection:
                apply_migrations(connection, Path(config.migrator.path))
        try:
            yield
        finally:
            if get_pii_detector.cache_info().currsize:
                get_pii_detector().close()
            database.dispose()

    application = FastAPI(title=API_NAME, lifespan=lifespan)
    application.add_exception_handler(APIError, api_error_handler)

    def get_service(session: Session = Depends(database.get_session), pii_detector: PiiDetector = Depends(get_pii_detector)) -> CommentsService:
        service_config = ServiceConfig(repository=CommentRepository(session), pii_detector=pii_detector)

        return CommentsService(config=service_config)

    token_validator = TokenValidator(
        auth_config
        or AuthConfig(
            disabled=config.auth.disabled,
            tenant_id=config.auth.tenant_id,
            audience=config.auth.token_audience,
            issuer_url=config.auth.issuer_url,
            jwks_url=config.auth.jwks_url,
            required_scope=config.auth.scope,
        )
    )

    user_dependency = token_validator.get_current_user
    application.state.user_dependency = user_dependency
    application.state.pii_dependency = get_pii_detector

    handler = CommentsHandler(
        service=get_service,
        user=user_dependency,
        prefix=config.api.prefix,
        tags=config.api.tags,
    )

    application.include_router(handler.router)

    return application