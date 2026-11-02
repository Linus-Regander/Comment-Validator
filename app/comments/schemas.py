from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class CommentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)

class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    user_id: str = Field(validation_alias="object_id")
    created_at: datetime
    updated_at: datetime