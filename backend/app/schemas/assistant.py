import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SavedRecord(BaseModel):
    """A record the assistant created or updated, shown as a link in the chat."""

    type: Literal["lead", "contact", "company", "activity", "note", "task"]
    action: Literal["created", "updated"]
    id: uuid.UUID
    label: str
    # The page to open for it: the record itself, or for activities/notes the record they're logged on.
    link_type: str | None = None
    link_id: uuid.UUID | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)
    # What the assistant saved in this turn, so later turns can refer back to those records.
    records: list[SavedRecord] = Field(default_factory=list)


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
