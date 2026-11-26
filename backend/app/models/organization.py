"""Organizations (tenants) and who belongs to them.

A `Profile` is a person's global login. What they can see and do depends on
their `Membership` in the organization they're working in: every CRM record
belongs to exactly one organization (see `app.db.tenancy`).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MembershipStatus, UserRole
from app.models.profile import Profile


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(100))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))


class Membership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's access to one organization, and their role in it."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_memberships_organization_user"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.SALES_REP)
    # "disabled" keeps the member listed (and their records attributed) but blocks access.
    status: Mapped[str] = mapped_column(String(20), default=MembershipStatus.ACTIVE)

    organization: Mapped[Organization] = relationship(lazy="joined")
    user: Mapped[Profile] = relationship(lazy="joined")

    @property
    def is_active(self) -> bool:
        return self.status == MembershipStatus.ACTIVE


class Invitation(UUIDPrimaryKeyMixin, Base):
    """An offer to join an organization, addressed to an email address.

    Whoever signs in with that (confirmed) email sees the invitation on their
    organizations page and can accept it; nothing else grants access.
    """

    __tablename__ = "invitations"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    # Stored lowercased. Re-inviting the same email refreshes the open invitation instead of adding one.
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.SALES_REP)
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship(lazy="joined")
    invited_by: Mapped[Profile | None] = relationship(lazy="joined")
