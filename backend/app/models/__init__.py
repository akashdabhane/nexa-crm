"""Import every model here so Alembic autogenerate and create_all can see them."""

from app.db.base import Base
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.lead import Lead
from app.models.note import Note
from app.models.notification import Notification
from app.models.pipeline import Pipeline, PipelineStage
from app.models.profile import Profile
from app.models.task import Task

__all__ = [
    "Activity",
    "AuditLog",
    "Base",
    "Company",
    "Contact",
    "Deal",
    "Lead",
    "Note",
    "Notification",
    "Pipeline",
    "PipelineStage",
    "Profile",
    "Task",
]
