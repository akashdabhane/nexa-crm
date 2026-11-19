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


class SocialPlatform(StrEnum):
    """Where a social lead came from (Lead.social_platform, LeadIntegration.platform)."""

    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"  # X
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    WHATSAPP = "whatsapp"
    OTHER = "other"


class IntegrationKind(StrEnum):
    # Native Meta Lead Ads: Facebook and Instagram lead forms on one Facebook Page.
    META_LEAD_ADS = "meta_lead_ads"
    # Generic inbound webhook (Zapier, Make, n8n, a custom script, ...): works for any platform.
    WEBHOOK = "webhook"


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
