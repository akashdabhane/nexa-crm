import uuid
from datetime import date, datetime

from pydantic import Field

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.common import EntityRef, InputSchema, ORMSchema
from app.schemas.profile import ProfileSummary


class TaskFields(InputSchema):
    description: str | None = None
    due_date: date | None = None
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    deal_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None


class TaskCreate(TaskFields):
    title: str = Field(min_length=1, max_length=255)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING


class TaskUpdate(TaskFields):
    title: str | None = Field(None, min_length=1, max_length=255)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None


class TaskRead(ORMSchema):
    id: uuid.UUID
    title: str
    description: str | None
    due_date: date | None
    priority: TaskPriority
    status: TaskStatus
    is_overdue: bool
    completed_at: datetime | None
    owner: ProfileSummary | None
    contact: EntityRef | None
    company: EntityRef | None
    deal: EntityRef | None
    created_at: datetime
    updated_at: datetime
