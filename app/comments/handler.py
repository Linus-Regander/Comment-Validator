from collections.abc import Callable

from fastapi import APIRouter, Depends, Response, status

from app.comments.schemas import CommentRead, CommentWrite
from app.comments.service import CommentsService
from app.util.token_validator import Principal


class CommentsHandler:
    def __init__(
        self,
        service: Callable[..., CommentsService],
        user: Callable[..., Principal],
        prefix: str,
        tags: list[str],
    ) -> None:
        self.router = APIRouter(prefix=prefix, tags=tags)
        router = self.router

        @router.get("", response_model=list[CommentRead])
        def get_comments(
            svc: CommentsService = Depends(service),
            user: Principal = Depends(user),
        ):
            return svc.get_comments(user=user)

        @router.get("/{comment_id}", response_model=CommentRead)
        def get_comment(
            comment_id: str,
            svc: CommentsService = Depends(service),
            user: Principal = Depends(user),
        ):
            return svc.get_comment(comment_id=comment_id, user=user)

        @router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
        def add_comment(
            data: CommentWrite,
            svc: CommentsService = Depends(service),
            user: Principal = Depends(user),
        ):
            return svc.add_comment(data=data, user=user)

        @router.put("/{comment_id}", response_model=CommentRead)
        def update_comment(
            comment_id: str,
            data: CommentWrite,
            svc: CommentsService = Depends(service),
            user: Principal = Depends(user),
        ):
            return svc.update_comment(comment_id=comment_id, data=data, user=user)

        @router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
        def delete_comment(
            comment_id: str,
            svc: CommentsService = Depends(service),
            user: Principal = Depends(user),
        ):
            svc.delete_comment(comment_id=comment_id, user=user)
            return Response(status_code=status.HTTP_204_NO_CONTENT)