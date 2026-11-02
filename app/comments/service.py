from uuid import uuid4

from dataclasses import dataclass

from app.comments.models import CommentRecord
from app.comments.repository import CommentRepository
from app.comments.schemas import CommentWrite
from app.errors import ForbiddenError, InvalidArgumentError, NotFoundError
from app.util.azure.pii import PiiDetector
from app.util.token_validator import Principal

ENTITY_NOT_FOUND = NotFoundError("Could not find entity")
ENTITY_FORBIDDEN_ACCESS = ForbiddenError("Caller does not have permission to access this entity")

@dataclass(frozen=True)
class ServiceConfig:
    repository: CommentRepository
    pii_detector: PiiDetector

class CommentsService:
    def __init__(self, config: ServiceConfig) -> None:
        self._repository = config.repository
        self._pii_detector = config.pii_detector

    def get_comments(self, user: Principal) -> list[CommentRecord]:
        return self._repository.list_all(user=user)

    def get_comment(self, comment_id: str, user: Principal) -> CommentRecord:
        record = self._repository.get(comment_id, user.tenant_id)
        if record is None:
            raise NotFoundError(ENTITY_NOT_FOUND)
        
        return record

    def add_comment(self, data: CommentWrite, user: Principal) -> CommentRecord:
        self._pii_detector.assert_clean(data.content)

        return self._repository.save(CommentRecord(
            id=str(uuid4()),
            content=data.content,
            tenant_id=user.tenant_id,
            object_id=user.object_id,
        ))

    def update_comment(self, comment_id: str, data: CommentWrite, user: Principal) -> CommentRecord:
        comment = self._repository.get(comment_id=comment_id)
        if comment is None:
            raise ENTITY_NOT_FOUND

        if comment.object_id is None or comment.object_id != user.object_id:
            raise ENTITY_FORBIDDEN_ACCESS

        if comment.tenant_id is None or comment.tenant_id != user.tenant_id:
            raise ENTITY_FORBIDDEN_ACCESS

        self._pii_detector.assert_clean(data.content)

        comment.content = data.content
        
        return self._repository.save(comment)

    def delete_comment(self, comment_id: str, user: Principal) -> None:
        comment = self._repository.get(comment_id=comment_id)
        if comment is None:
            raise ENTITY_NOT_FOUND
        
        if comment.object_id is None or comment.object_id != user.object_id:
            raise ENTITY_FORBIDDEN_ACCESS

        if comment.tenant_id is None or comment.tenant_id != user.tenant_id:
            raise ENTITY_FORBIDDEN_ACCESS
        
        self._repository.delete(comment)