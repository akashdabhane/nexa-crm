import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IntegrationKind
from app.models.profile import Profile


class LeadIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A connection that brings leads in from a social platform.

    - `meta_lead_ads`: a Facebook Page whose Facebook/Instagram lead forms are
      received through Meta's webhook and can be pulled with "Sync now".
    - `webhook`: a secret URL that any tool (Zapier, Make, n8n, a script) can
      POST leads to, for platforms without a usable public lead API (X, LinkedIn, TikTok...).
    """

    __tablename__ = "lead_integrations"

    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20), default=IntegrationKind.WEBHOOK)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Secret part of the inbound webhook URL (/api/integrations/webhooks/{token}).
    webhook_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Meta Lead Ads only.
    meta_page_id: Mapped[str | None] = mapped_column(String(50), index=True)
    meta_page_name: Mapped[str | None] = mapped_column(String(255))
    access_token_encrypted: Mapped[str | None] = mapped_column(Text)

    # Applied to every imported lead.
    default_owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))
    default_score: Mapped[int] = mapped_column(Integer, default=0)

    leads_imported: Mapped[int] = mapped_column(Integer, default=0)
    last_lead_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))

    default_owner: Mapped[Profile | None] = relationship(foreign_keys=[default_owner_id], lazy="joined")

    @property
    def has_access_token(self) -> bool:
        return bool(self.access_token_encrypted)
