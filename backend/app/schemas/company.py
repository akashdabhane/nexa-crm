import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import InputSchema, ORMSchema
from app.schemas.profile import ProfileSummary


class CompanyBase(InputSchema):
    name: str = Field(min_length=1, max_length=255)
    industry: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    employee_count: int | None = Field(None, ge=0)


class CompanyCreate(CompanyBase):
    owner_id: uuid.UUID | None = None


class CompanyUpdate(InputSchema):
    name: str | None = Field(None, min_length=1, max_length=255)
    industry: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    employee_count: int | None = Field(None, ge=0)
    owner_id: uuid.UUID | None = None


class CompanyRead(ORMSchema):
    id: uuid.UUID
    name: str
    industry: str | None
    website: str | None
    email: str | None
    phone: str | None
    address: str | None
    city: str | None
    country: str | None
    employee_count: int | None
    owner: ProfileSummary | None
    created_at: datetime
    updated_at: datetime
    contact_count: int = 0
    deal_count: int = 0
    open_deal_value: float = 0
