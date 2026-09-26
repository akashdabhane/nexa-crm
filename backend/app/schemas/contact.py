import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.models.enums import ContactStatus
from app.schemas.common import EntityRef, InputSchema, ORMSchema
from app.schemas.profile import ProfileSummary


def _clean_tags(tags: list[str] | None) -> list[str] | None:
    """Trim, drop empties and de-duplicate (case-insensitively) while keeping order."""
    if tags is None:
        return None
    seen: set[str] = set()
    cleaned = []
    for tag in tags:
        tag = tag.strip()[:50]
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            cleaned.append(tag)
    return cleaned


class ContactFields(InputSchema):
    last_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    job_title: str | None = Field(None, max_length=150)
    website: str | None = Field(None, max_length=255)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    company_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None

    @field_validator("tags", check_fields=False)
    @classmethod
    def clean_tags(cls, tags: list[str] | None) -> list[str] | None:
        return _clean_tags(tags)


class ContactCreate(ContactFields):
    first_name: str = Field(min_length=1, max_length=100)
    status: ContactStatus = ContactStatus.ACTIVE
    tags: list[str] = Field(default_factory=list, max_length=20)


class ContactUpdate(ContactFields):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    status: ContactStatus | None = None
    tags: list[str] | None = Field(None, max_length=20)


class ContactRead(ORMSchema):
    id: uuid.UUID
    first_name: str
    last_name: str | None
    full_name: str
    email: str | None
    phone: str | None
    job_title: str | None
    website: str | None
    address: str | None
    city: str | None
    country: str | None
    status: ContactStatus
    tags: list[str]
    company: EntityRef | None
    owner: ProfileSummary | None
    created_at: datetime
    updated_at: datetime
