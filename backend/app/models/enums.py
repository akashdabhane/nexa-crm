"""Enumerations shared by models and schemas.

Stored as VARCHAR in the database (not native Postgres enums) so adding a
value never requires a tricky migration; Pydantic validates incoming values.
"""

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    SALES_REP = "sales_rep"


class ContactStatus(StrEnum):
    ACTIVE = "active"
    CUSTOMER = "customer"
    INACTIVE = "inactive"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"


class LeadSource(StrEnum):
    WEBSITE = "website"
    REFERRAL = "referral"
    ADVERTISEMENT = "advertisement"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    COLD_CALL = "cold_call"
    OTHER = "other"


class StageType(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"


class DealStatus(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"


class ActivityType(StrEnum):
    CALL = "call"
    MEETING = "meeting"
    EMAIL = "email"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(StrEnum):
    LEAD_ASSIGNED = "lead_assigned"
    DEAL_ASSIGNED = "deal_assigned"
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE = "task_due"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
