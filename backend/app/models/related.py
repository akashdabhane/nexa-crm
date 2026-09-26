"""Mixin for records that attach to contacts / companies / leads / deals.

Uses plain nullable foreign keys (not a polymorphic entity_type/entity_id pair),
so the database enforces integrity and one record can appear on several
timelines at once, e.g. a call with a contact about a specific deal.
"""

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship


class RelatedRecordsMixin:
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("deals.id", ondelete="SET NULL"), index=True)

    @declared_attr
    def contact(cls) -> Mapped["Contact | None"]:  # noqa: F821
        return relationship("Contact", lazy="selectin")

    @declared_attr
    def company(cls) -> Mapped["Company | None"]:  # noqa: F821
        return relationship("Company", lazy="selectin")

    @declared_attr
    def deal(cls) -> Mapped["Deal | None"]:  # noqa: F821
        return relationship("Deal", lazy="selectin")


class LeadLinkMixin:
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), index=True)

    @declared_attr
    def lead(cls) -> Mapped["Lead | None"]:  # noqa: F821
        return relationship("Lead", lazy="selectin")
