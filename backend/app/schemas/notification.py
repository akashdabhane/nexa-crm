import uuid
from datetime import datetime

from app.models.enums import NotificationType
from app.schemas.common import ORMSchema
from app.schemas.profile import ProfileSummary


class NotificationRead(ORMSchema):
    id: uuid.UUID
    type: NotificationType
    title: str
    message: str | None
    entity_type: str | None
    entity_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


class AuditLogRead(ORMSchema):
    id: uuid.UUID
    user: ProfileSummary | None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    details: dict
    created_at: datetime
