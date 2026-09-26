import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import EmailStr, Field

from app.models.enums import LeadSource, LeadStatus
from app.schemas.common import InputSchema, ORMSchema
from app.schemas.profile import ProfileSummary


class LeadCreate(InputSchema):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    company_name: str | None = Field(None, max_length=255)
    source: LeadSource = LeadSource.OTHER
    status: LeadStatus = LeadStatus.NEW
    score: int = Field(0, ge=0, le=100)
    owner_id: uuid.UUID | None = None


class LeadUpdate(InputSchema):
    name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    company_name: str | None = Field(None, max_length=255)
    source: LeadSource | None = None
    status: LeadStatus | None = None
    score: int | None = Field(None, ge=0, le=100)
    owner_id: uuid.UUID | None = None


class LeadRead(ORMSchema):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    company_name: str | None
    source: LeadSource
    status: LeadStatus
    score: int
    owner: ProfileSummary | None
    converted_at: datetime | None
    converted_contact_id: uuid.UUID | None
    converted_company_id: uuid.UUID | None
    converted_deal_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class LeadConvert(InputSchema):
    """Options for Lead -> Contact + Company + Deal conversion."""

    # Link to an existing company instead of matching/creating one by name.
    company_id: uuid.UUID | None = None
    create_deal: bool = True
    deal_name: str | None = Field(None, max_length=255)
    deal_value: Decimal = Field(Decimal(0), ge=0, max_digits=14, decimal_places=2)
    expected_close_date: date | None = None


class LeadConvertResult(ORMSchema):
    lead: LeadRead
    contact_id: uuid.UUID
    company_id: uuid.UUID | None
    deal_id: uuid.UUID | None
