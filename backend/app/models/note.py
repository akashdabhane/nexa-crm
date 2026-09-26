import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.profile import Profile
from app.models.related import LeadLinkMixin, RelatedRecordsMixin


class Note(UUIDPrimaryKeyMixin, TimestampMixin, RelatedRecordsMixin, LeadLinkMixin, Base):
    __tablename__ = "notes"

    body: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"), index=True)
    owner: Mapped[Profile | None] = relationship(lazy="joined")
