from collections.abc import Generator, Mapping
from dataclasses import dataclass, field

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

MISSING_URL_ERROR = "Database URL must not be empty"

class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

@dataclass(frozen=True)
class DatabaseConfig:
    url: str
    pool_pre_ping: bool = True
    echo: bool = False
    connect_args: Mapping[str, object] = field(default_factory=dict)

class Database:
    def __init__(self, config: DatabaseConfig) -> None:
        if not config.url:
            raise ValueError(MISSING_URL_ERROR)

        self._engine = create_engine(
            config.url,
            pool_pre_ping=config.pool_pre_ping,
            echo=config.echo,
            connect_args=dict(config.connect_args),
        )
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False)

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        return self._session_factory

    def get_session(self) -> Generator[Session, None, None]:
        with self._session_factory() as session:
            yield session

    def dispose(self) -> None:
        self._engine.dispose()