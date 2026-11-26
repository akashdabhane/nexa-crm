import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.tenancy import OrgScopedMixin
from app.models.enums import LeadSource, LeadStatus
from app.models.profile import Profile


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, OrgScopedMixin, Base):
    __tablename__ = "leads"
    # An imported lead (e.g. a Meta leadgen id) is only created once per platform in each organization.
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "social_platform", "external_id", name="uq_leads_organization_platform_external_id"
        ),
    )

    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    company_name: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(30), default=LeadSource.OTHER, index=True)
    status: Mapped[str] = mapped_column(String(20), default=LeadStatus.NEW, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)

    # Social media origin. Set by imports (webhooks, Meta Lead Ads, CSV) or by hand.
    social_platform: Mapped[str | None] = mapped_column(String(20), index=True)
    social_handle: Mapped[str | None] = mapped_column(String(255))  # @username or profile URL
    external_id: Mapped[str | None] = mapped_column(String(100))  # the platform's lead id, for de-duplication
    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lead_integrations.id", ondelete="SET NULL"), index=True
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"), index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))

    # Filled in when the lead is converted.
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    converted_company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    converted_deal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("deals.id", ondelete="SET NULL"))

    owner: Mapped[Profile | None] = relationship(foreign_keys=[owner_id], lazy="joined")
