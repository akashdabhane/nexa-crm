import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import InputSchema
from app.schemas.profile import ProfileSummary
from app.schemas.related import LinksRead, RequiredLinksInput


class NoteCreate(RequiredLinksInput):
    body: str = Field(min_length=1, max_length=10_000)


class NoteUpdate(InputSchema):
    body: str = Field(min_length=1, max_length=10_000)


class NoteRead(LinksRead):
    id: uuid.UUID
    body: str
    owner: ProfileSummary | None
    created_at: datetime
    updated_at: datetime
