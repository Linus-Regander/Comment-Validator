"""REST routes for the comments resource."""

from fastapi import APIRouter, Depends, Query, Response, status
from functools import lru_cache
from sqlalchemy.orm import Session

from app.comments.handler import CommentsHandler
from app.comments.repository import CommentRepository
from app.comments.schemas import CommentRead, CommentWrite
from app.comments.service import CommentsService
from app.database import get_db
from app.pii import AzurePiiDetector, PiiDetector
from app.security import EntraPrincipal, get_current_user
from app.users.repository import UserRepository


router = APIRouter(prefix="/comments", tags=["comments"])


@lru_cache(maxsize=1)
def get_pii_detector() -> AzurePiiDetector:
    return AzurePiiDetector()


def close_pii_detector() -> None:
    """Close the cached Azure client when one was created."""
    if get_pii_detector.cache_info().currsize:
        get_pii_detector().close()
        get_pii_detector.cache_clear()


def get_handler(
    session: Session = Depends(get_db),
    pii_detector: PiiDetector = Depends(get_pii_detector),
) -> CommentsHandler:
    user_repository = UserRepository(session)
    repository = CommentRepository(session, user_repository)
    service = CommentsService(repository, pii_detector)
    return CommentsHandler(service)


@router.get("", response_model=list[CommentRead])
def list_comments(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    handler: CommentsHandler = Depends(get_handler),
    principal: EntraPrincipal = Depends(get_current_user),
) -> list[CommentRead]:
    return handler.list_comments(principal, skip=skip, limit=limit)


@router.get("/{comment_id}", response_model=CommentRead)
def get_comment(
    comment_id: str,
    handler: CommentsHandler = Depends(get_handler),
    principal: EntraPrincipal = Depends(get_current_user),
) -> CommentRead:
    return handler.get_comment(comment_id, principal)


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def push_comment(
    data: CommentWrite,
    handler: CommentsHandler = Depends(get_handler),
    principal: EntraPrincipal = Depends(get_current_user),
) -> CommentRead:
    return handler.push_comment(data, principal)


@router.put("/{comment_id}", response_model=CommentRead)
def put_comment(
    comment_id: str,
    data: CommentWrite,
    handler: CommentsHandler = Depends(get_handler),
    principal: EntraPrincipal = Depends(get_current_user),
) -> CommentRead:
    return handler.put_comment(comment_id, data, principal)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: str,
    handler: CommentsHandler = Depends(get_handler),
    principal: EntraPrincipal = Depends(get_current_user),
) -> Response:
    handler.delete_comment(comment_id, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)