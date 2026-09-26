import uuid

from pydantic import model_validator

from app.schemas.common import EntityRef, InputSchema, ORMSchema

LINK_FIELDS = ("contact_id", "company_id", "lead_id", "deal_id")


class LinksInput(InputSchema):
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    deal_id: uuid.UUID | None = None


class RequiredLinksInput(LinksInput):
    """Activities and notes must belong to at least one record."""

    @model_validator(mode="after")
    def at_least_one_link(self):
        if not any(getattr(self, field, None) for field in LINK_FIELDS):
            raise ValueError("Link this to at least one contact, company, lead or deal")
        return self


class LinksRead(ORMSchema):
    contact: EntityRef | None = None
    company: EntityRef | None = None
    lead: EntityRef | None = None
    deal: EntityRef | None = None
