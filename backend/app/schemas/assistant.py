import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ExportFormat = Literal["xlsx", "docx", "pptx", "md"]
ListableType = Literal["lead", "contact", "company", "deal", "task"]


class SavedRecord(BaseModel):
    """A record the assistant created or updated, shown as a link in the chat."""

    type: Literal["lead", "contact", "company", "activity", "note", "task"]
    action: Literal["created", "updated"]
    id: uuid.UUID
    label: str
    # The page to open for it: the record itself, or for activities/notes the record they're logged on.
    link_type: str | None = None
    link_id: uuid.UUID | None = None


class RecordFilters(BaseModel):
    """Which records a list shows (and an export of it contains). Team members are given by name or email."""

    record_type: ListableType
    search: str | None = Field(None, max_length=200)
    created_by: str | None = Field(None, max_length=200)
    owner: str | None = Field(None, max_length=200)
    status: str | None = Field(None, max_length=30)
    source: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=100)  # city, country or address (companies and contacts)
    created_from: date | None = None
    created_to: date | None = None


class ExportOffer(RecordFilters):
    """A list the assistant just showed, which the user can download as a file without another model call."""

    total: int
    label: str  # e.g. "12 contacts created by Riya Sharma"


class ExportedFile(BaseModel):
    """A file the assistant made, sent inline (base64) so the stateless server never has to store it."""

    filename: str
    format: ExportFormat
    mime_type: str
    content_base64: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)
    # What the assistant saved in this turn, so later turns can refer back to those records.
    records: list[SavedRecord] = Field(default_factory=list)
    # The list it showed (so "yes, export it" can reuse the same filters) and the files it made, by name.
    export_offer: ExportOffer | None = None
    files: list[str] = Field(default_factory=list, max_length=10)


class ChatRequest(BaseModel):
    """The whole conversation so far; the server keeps no chat state."""

    messages: list[ChatMessage] = Field(min_length=1, max_length=50)

    @field_validator("messages")
    @classmethod
    def ends_with_user_message(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        if messages[-1].role != "user":
            raise ValueError("The last message must be from the user")
        return messages


class ChatResponse(BaseModel):
    reply: str
    records: list[SavedRecord]
    files: list[ExportedFile] = Field(default_factory=list)
    export_offer: ExportOffer | None = None


class ExportRequest(BaseModel):
    """Download a list the assistant offered (the chat's export buttons), skipping the model."""

    filters: RecordFilters
    format: ExportFormat


class TranscriptionResponse(BaseModel):
    text: str  # empty when no speech was heard
