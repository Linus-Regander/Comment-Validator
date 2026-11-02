from sqlalchemy import select
from sqlalchemy.orm import Session

from app.comments.models import CommentRecord
from app.util.token_validator import Principal

class CommentRepository:
    def __init__(self, session: Session,) -> None:
        self._session = session

    def list_all(self, user: Principal) -> list[CommentRecord]:
        return list(self._session.scalars(select(CommentRecord).where(CommentRecord.tenant_id == user.tenant_id)))

    def get(self, comment_id: str, tenant_id: str) -> CommentRecord | None:
        stmt = select(CommentRecord).where(
            CommentRecord.id == comment_id,
            CommentRecord.tenant_id == tenant_id,
        )
        
        return self._session.scalars(stmt).first()

    def save(self, comment: CommentRecord) -> CommentRecord:
        self._session.add(comment)
        self._session.commit()
        self._session.refresh(comment)

        return comment

    def delete(self, comment: CommentRecord) -> None:
        self._session.delete(comment)
        self._session.commit()