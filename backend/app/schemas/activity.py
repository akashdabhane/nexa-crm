import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import ActivityType
from app.schemas.profile import ProfileSummary
from app.schemas.related import LinksInput, LinksRead, RequiredLinksInput


class ActivityCreate(RequiredLinksInput):
    type: ActivityType
    subject: str = Field(min_length=1, max_length=255)
    description: str | None = None
    occurred_at: datetime | None = None  # defaults to now
    duration_minutes: int | None = Field(None, ge=0, le=24 * 60)


class ActivityUpdate(LinksInput):
    type: ActivityType | None = None
    subject: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    occurred_at: datetime | None = None
    duration_minutes: int | None = Field(None, ge=0, le=24 * 60)


class ActivityRead(LinksRead):
    id: uuid.UUID
    type: ActivityType
    subject: str
    description: str | None
    occurred_at: datetime
    duration_minutes: int | None
    owner: ProfileSummary | None
    created_at: datetime
