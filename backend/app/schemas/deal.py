import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.models.enums import DealStatus
from app.schemas.common import EntityRef, InputSchema, ORMSchema
from app.schemas.pipeline import StageRead
from app.schemas.profile import ProfileSummary


class DealFields(InputSchema):
    expected_close_date: date | None = None
    company_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    description: str | None = None

    @field_validator("currency", check_fields=False)
    @classmethod
    def upper_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class DealCreate(DealFields):
    name: str = Field(min_length=1, max_length=255)
    value: Decimal = Field(Decimal(0), ge=0, max_digits=14, decimal_places=2)
    currency: str = Field("USD", pattern=r"^[A-Za-z]{3}$")
    pipeline_id: uuid.UUID | None = None  # default pipeline when omitted
    stage_id: uuid.UUID | None = None  # first stage when omitted
    probability: int | None = Field(None, ge=0, le=100)  # stage default when omitted


class DealUpdate(DealFields):
    name: str | None = Field(None, min_length=1, max_length=255)
    value: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(None, pattern=r"^[A-Za-z]{3}$")
    stage_id: uuid.UUID | None = None
    probability: int | None = Field(None, ge=0, le=100)


class DealStageUpdate(InputSchema):
    stage_id: uuid.UUID


class DealRead(ORMSchema):
    id: uuid.UUID
    name: str
    value: float
    currency: str
    pipeline_id: uuid.UUID
    stage: StageRead
    status: DealStatus
    probability: int
    expected_close_date: date | None
    closed_at: datetime | None
    company: EntityRef | None
    contact: EntityRef | None
    owner: ProfileSummary | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class BoardColumn(ORMSchema):
    stage: StageRead
    deals: list[DealRead]
    count: int
    total_value: float


class DealBoard(ORMSchema):
    pipeline_id: uuid.UUID
    columns: list[BoardColumn]
