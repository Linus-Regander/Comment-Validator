"""Pydantic request and response schemas for comments."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentWrite(BaseModel):
    """Fields accepted when creating or replacing a comment."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)


class CommentRead(BaseModel):
    """Comment representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    user_id: int | None
    created_at: datetime
    updated_at: datetime