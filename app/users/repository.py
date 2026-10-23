"""Database operations for Entra user identities."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.security import EntraPrincipal
from app.users.models import UserRecord


class UserRepository:
    """Find or persist the minimal identity represented by a verified token."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self, principal: EntraPrincipal) -> UserRecord:
        statement = select(UserRecord).where(
            UserRecord.tenant_id == principal.tenant_id,
            UserRecord.entra_object_id == principal.object_id,
        )
        user = self._session.scalar(statement)
        if user is not None:
            return user

        user = UserRecord(
            tenant_id=principal.tenant_id,
            entra_object_id=principal.object_id,
        )
        self._session.add(user)
        try:
            self._session.flush()
        except IntegrityError:
            self._session.rollback()
            user = self._session.scalar(statement)
            if user is None:
                raise
        return user