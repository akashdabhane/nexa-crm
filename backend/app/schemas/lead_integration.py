import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationKind, SocialPlatform
from app.schemas.common import InputSchema, ORMSchema
from app.schemas.profile import ProfileSummary

META_PAGE_ID = r"^\d{1,50}$"


class IntegrationCreate(InputSchema):
    name: str = Field(min_length=1, max_length=100)
    kind: IntegrationKind = IntegrationKind.WEBHOOK
    # For Meta Lead Ads: the platform used when Meta doesn't say (facebook or instagram).
    platform: SocialPlatform = SocialPlatform.OTHER
    is_active: bool = True
    meta_page_id: str | None = Field(None, pattern=META_PAGE_ID)
    access_token: str | None = Field(None, min_length=10, max_length=2000)  # write-only
    default_owner_id: uuid.UUID | None = None
    default_score: int = Field(0, ge=0, le=100)


class IntegrationUpdate(InputSchema):
    name: str | None = Field(None, min_length=1, max_length=100)
    platform: SocialPlatform | None = None
    is_active: bool | None = None
    meta_page_id: str | None = Field(None, pattern=META_PAGE_ID)
    access_token: str | None = Field(None, min_length=10, max_length=2000)
    default_owner_id: uuid.UUID | None = None
    default_score: int | None = Field(None, ge=0, le=100)


class IntegrationRead(ORMSchema):
    id: uuid.UUID
    name: str
    kind: IntegrationKind
    platform: SocialPlatform
    is_active: bool
    webhook_token: str
    meta_page_id: str | None
    meta_page_name: str | None
    has_access_token: bool
    default_owner: ProfileSummary | None
    default_score: int
    leads_imported: int
    last_lead_at: datetime | None
    last_synced_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class IntegrationSetup(BaseModel):
    """Which server-side settings are in place, so the UI can explain what's missing."""

    meta_webhook_ready: bool  # META_APP_SECRET + META_VERIFY_TOKEN
    token_storage_ready: bool  # INTEGRATIONS_SECRET


class ImportIssue(BaseModel):
    row: int  # 1-based position in the CSV / webhook batch
    name: str | None
    reason: str


class LeadPreview(BaseModel):
    name: str
    email: str | None
    phone: str | None
    company_name: str | None
    social_platform: SocialPlatform | None
    social_handle: str | None


class ImportResult(BaseModel):
    created: int
    skipped: int  # duplicates
    failed: int  # rows that couldn't become a lead
    lead_ids: list[uuid.UUID]
    issues: list[ImportIssue]  # first 50 skipped/failed rows
    preview: list[LeadPreview] = []  # dry runs only: the first rows that would be created
    columns: list[str] = []  # CSV only: the header row
    has_more: bool = False  # Meta sync only: it hit the per-sync limit; "Sync now" again for the rest


class CsvImport(InputSchema):
    csv_text: str = Field(min_length=1, max_length=5_000_000)
    # Marks every row as coming from this platform (a row's own "platform" column wins).
    platform: SocialPlatform | None = None
    owner_id: uuid.UUID | None = None
    score: int = Field(0, ge=0, le=100)
    dry_run: bool = False
