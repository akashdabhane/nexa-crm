import uuid

from pydantic import Field

from app.models.enums import StageType
from app.schemas.common import InputSchema, ORMSchema


class StageRead(ORMSchema):
    id: uuid.UUID
    name: str
    position: int
    probability: int
    stage_type: StageType


class PipelineRead(ORMSchema):
    id: uuid.UUID
    name: str
    is_default: bool
    stages: list[StageRead]


class StageInput(InputSchema):
    name: str = Field(min_length=1, max_length=100)
    probability: int = Field(0, ge=0, le=100)
    stage_type: StageType = StageType.OPEN


class PipelineCreate(InputSchema):
    name: str = Field(min_length=1, max_length=100)
    stages: list[StageInput] = Field(min_length=2, max_length=20)


class StageUpdate(InputSchema):
    name: str | None = Field(None, min_length=1, max_length=100)
    probability: int | None = Field(None, ge=0, le=100)
