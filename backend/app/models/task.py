import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TaskPriority, TaskStatus
from app.models.profile import Profile
from app.models.related import RelatedRecordsMixin


class Task(UUIDPrimaryKeyMixin, TimestampMixin, RelatedRecordsMixin, Base):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    priority: Mapped[str] = mapped_column(String(10), default=TaskPriority.MEDIUM)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set once a "task due" notification has been sent, so it's only sent once.
    due_notified: Mapped[bool] = mapped_column(Boolean, default=False)

    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"), index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))

    owner: Mapped[Profile | None] = relationship(foreign_keys=[owner_id], lazy="joined")

    @property
    def is_overdue(self) -> bool:
        return (
            self.due_date is not None
            and self.due_date < date.today()
            and self.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        )
