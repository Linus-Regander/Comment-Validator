"""Business operations for comments."""

from uuid import uuid4

from app.comments.models import CommentRecord
from app.comments.repository import CommentRepository
from app.comments.schemas import CommentWrite
from app.errors import CommentForbiddenError, CommentNotFoundError
from app.pii import PiiDetector
from app.security import EntraPrincipal


class CommentsService:
    """Apply comment operations using the repository layer."""

    def __init__(self, repository: CommentRepository, pii_detector: PiiDetector) -> None:
        self._repository = repository
        self._pii_detector = pii_detector

    def list_comments(
        self,
        principal: EntraPrincipal,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CommentRecord]:
        return self._repository.list(principal=principal, skip=skip, limit=limit)

    def get_comment(self, comment_id: str, principal: EntraPrincipal) -> CommentRecord:
        comment = self._repository.get(comment_id)
        if comment is None or comment.user is None:
            raise CommentNotFoundError(comment_id)
        if (
            comment.user.tenant_id != principal.tenant_id
            or comment.user.entra_object_id != principal.object_id
        ):
            raise CommentForbiddenError("Only the comment owner can read it")
        return comment

    def push_comment(
        self,
        data: CommentWrite,
        principal: EntraPrincipal,
    ) -> CommentRecord:
        self._pii_detector.assert_clean(data.content)
        user = self._repository.get_or_create_user(principal)
        comment = CommentRecord(
            id=str(uuid4()),
            content=data.content,
            user=user,
        )
        return self._repository.save(comment)

    def put_comment(
        self,
        comment_id: str,
        data: CommentWrite,
        principal: EntraPrincipal,
    ) -> CommentRecord:
        comment = self._repository.get(comment_id)
        if comment is not None and (
            comment.user is None
            or comment.user.tenant_id != principal.tenant_id
            or comment.user.entra_object_id != principal.object_id
        ):
            raise CommentForbiddenError("Only the comment owner can update it")

        self._pii_detector.assert_clean(data.content)
        user = self._repository.get_or_create_user(principal)
        if comment is None:
            comment = CommentRecord(
                id=comment_id,
                content=data.content,
                user=user,
            )
        else:
            comment.content = data.content
        return self._repository.save(comment)

    def delete_comment(self, comment_id: str, principal: EntraPrincipal) -> None:
        comment = self.get_comment(comment_id, principal)
        if (
            comment.user is None
            or comment.user.tenant_id != principal.tenant_id
            or comment.user.entra_object_id != principal.object_id
        ):
            raise CommentForbiddenError("Only the comment owner can delete it")
        self._repository.delete(comment)