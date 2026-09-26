import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class ProfileSummary(BaseModel):
    """Compact user representation embedded in other resources (e.g. owner)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class ProfileUpdateMe(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


class ProfileUpdateAdmin(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
