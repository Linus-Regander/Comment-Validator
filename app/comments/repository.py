"""Database access for comment records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.comments.models import CommentRecord
from app.security import EntraPrincipal
from app.users.repository import UserRepository


class CommentRepository:
    """Encapsulate SQLAlchemy operations for comments."""

    def __init__(
        self,
        session: Session,
        user_repository: UserRepository,
    ) -> None:
        self._session = session
        self._user_repository = user_repository

    def get_or_create_user(self, principal: EntraPrincipal):
        return self._user_repository.get_or_create(principal)

    def list(
        self,
        principal: EntraPrincipal,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CommentRecord]:
        statement = (
            select(CommentRecord)
            .join(CommentRecord.user)
            .where(
                CommentRecord.user.has(
                    tenant_id=principal.tenant_id,
                    entra_object_id=principal.object_id,
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self._session.scalars(statement))

    def get(self, comment_id: str) -> CommentRecord | None:
        return self._session.get(CommentRecord, comment_id)

    def save(self, comment: CommentRecord) -> CommentRecord:
        self._session.add(comment)
        self._session.commit()
        self._session.refresh(comment)
        return comment

    def delete(self, comment: CommentRecord) -> None:
        self._session.delete(comment)
        self._session.commit()