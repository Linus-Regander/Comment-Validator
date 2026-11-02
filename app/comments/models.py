from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

class CommentRecord(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_owner", "tenant_id", "object_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )