"""Persisted identities for Microsoft Entra users."""

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRecord(Base):
    """Minimal tenant-scoped Entra identity associated with comments."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entra_object_id", name="uq_user_entra_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entra_object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    comments: Mapped[list["CommentRecord"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )