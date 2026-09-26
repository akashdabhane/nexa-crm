import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.profile import Profile
from app.models.related import LeadLinkMixin, RelatedRecordsMixin


class Activity(UUIDPrimaryKeyMixin, TimestampMixin, RelatedRecordsMixin, LeadLinkMixin, Base):
    """A logged interaction: call, meeting or email."""

    __tablename__ = "activities"

    type: Mapped[str] = mapped_column(String(20), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"), index=True)
    owner: Mapped[Profile | None] = relationship(lazy="joined")
