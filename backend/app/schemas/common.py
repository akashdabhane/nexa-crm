import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class Page[T](BaseModel):
    """Paginated list response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class InputSchema(BaseModel):
    """Base for request bodies.

    HTML forms send "" for untouched optional fields; treat those as null so
    e.g. an empty email doesn't fail email validation.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def blank_strings_to_none(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {key: (None if value == "" else value) for key, value in data.items()}
        return data


class ORMSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EntityRef(ORMSchema):
    """Minimal reference to a related record, e.g. a contact's company."""

    id: uuid.UUID
    name: str
