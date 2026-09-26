import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole


class Profile(TimestampMixin, Base):
    """Application user. `id` is the Supabase auth user id (JWT `sub`)."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.SALES_REP)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def is_manager_or_admin(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.MANAGER)
