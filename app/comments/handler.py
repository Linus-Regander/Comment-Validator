"""Translate request operations into service calls."""

from app.comments.models import CommentRecord
from app.comments.schemas import CommentWrite
from app.comments.service import CommentsService
from app.security import EntraPrincipal


class CommentsHandler:
    """Handle request operations and map domain errors to HTTP responses."""

    def __init__(self, service: CommentsService) -> None:
        self._service = service

    def list_comments(
        self,
        principal: EntraPrincipal,
        skip: int,
        limit: int,
    ) -> list[CommentRecord]:
        return self._service.list_comments(principal, skip=skip, limit=limit)

    def get_comment(
        self,
        comment_id: str,
        principal: EntraPrincipal,
    ) -> CommentRecord:
        return self._service.get_comment(comment_id, principal)

    def push_comment(
        self,
        data: CommentWrite,
        principal: EntraPrincipal,
    ) -> CommentRecord:
        return self._service.push_comment(data, principal)

    def put_comment(
        self,
        comment_id: str,
        data: CommentWrite,
        principal: EntraPrincipal,
    ) -> CommentRecord:
        return self._service.put_comment(comment_id, data, principal)

    def delete_comment(self, comment_id: str, principal: EntraPrincipal) -> None:
        self._service.delete_comment(comment_id, principal)