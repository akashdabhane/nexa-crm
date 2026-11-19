"""Turning social-media lead data (CSV exports, webhook payloads, Meta lead forms) into leads.

Every import path goes through `import_rows`, so field mapping, de-duplication,
audit entries and notifications behave the same everywhere:

- Column names are matched loosely ("Full Name", "full_name", "fullName" all work),
  covering the exports of Facebook/Instagram, LinkedIn, TikTok and typical Zapier/Make payloads.
- A row is skipped when the platform's lead id was already imported, or a lead
  with the same email exists (in the CRM or earlier in the same batch).
- Unmapped fields (custom form questions, campaign names, ...) are kept as a note on the lead.
"""

import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Lead, LeadIntegration, Note, Profile
from app.models.enums import LeadSource, LeadStatus, NotificationType, SocialPlatform
from app.services import audit, notifications

MAX_ROWS = 5000
MAX_ISSUES = 50
PREVIEW_ROWS = 10

PLATFORM_LABELS = {
    SocialPlatform.FACEBOOK: "Facebook",
    SocialPlatform.INSTAGRAM: "Instagram",
    SocialPlatform.TWITTER: "X (Twitter)",
    SocialPlatform.LINKEDIN: "LinkedIn",
    SocialPlatform.TIKTOK: "TikTok",
    SocialPlatform.YOUTUBE: "YouTube",
    SocialPlatform.WHATSAPP: "WhatsApp",
    SocialPlatform.OTHER: "social media",
}

# Values platforms and tools use for themselves -> SocialPlatform.
PLATFORM_ALIASES = {
    "fb": SocialPlatform.FACEBOOK,
    "facebook": SocialPlatform.FACEBOOK,
    "messenger": SocialPlatform.FACEBOOK,
    "an": SocialPlatform.FACEBOOK,  # Meta Audience Network
    "ig": SocialPlatform.INSTAGRAM,
    "instagram": SocialPlatform.INSTAGRAM,
    "x": SocialPlatform.TWITTER,
    "twitter": SocialPlatform.TWITTER,
    "x_twitter": SocialPlatform.TWITTER,
    "linkedin": SocialPlatform.LINKEDIN,
    "tiktok": SocialPlatform.TIKTOK,
    "youtube": SocialPlatform.YOUTUBE,
    "whatsapp": SocialPlatform.WHATSAPP,
    "wa": SocialPlatform.WHATSAPP,
}

# Normalized column name -> lead field. The first matching column wins.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("full_name", "name", "fullname", "contact_name", "lead_name", "your_name"),
    "first_name": ("first_name", "firstname", "given_name", "fname"),
    "last_name": ("last_name", "lastname", "surname", "family_name", "lname"),
    "email": ("email", "email_address", "work_email", "e_mail", "business_email", "mail"),
    "phone": (
        "phone_number", "phone", "mobile", "mobile_number", "mobile_phone", "telephone",
        "work_phone_number", "contact_number", "whatsapp_number", "cell", "cell_phone",
    ),
    "company_name": ("company_name", "company", "organization", "organisation", "business_name", "employer"),
    "social_handle": (
        "social_handle", "handle", "username", "user_name", "profile_url", "instagram_username",
        "instagram_handle", "twitter_handle", "twitter_username", "x_handle", "tiktok_username",
        "linkedin_profile_url", "linkedin_profile", "linkedin_url", "profile",
    ),
    "external_id": ("external_id", "lead_id", "leadgen_id", "id"),
    "platform": ("platform", "social_platform", "network", "channel"),
    "score": ("score", "lead_score"),
    "source": ("source", "lead_source"),
}
# Bookkeeping columns from Meta/LinkedIn exports that add nothing to a note.
IGNORED_EXTRAS = {"is_organic", "inbox_url", "created_time", "lead_status", "retailer_item_id"}

_MAPPED_COLUMNS = {alias for aliases in FIELD_ALIASES.values() for alias in aliases}


def normalize_key(key: str) -> str:
    """'Full Name' / 'full-name' / 'fullName' / 'E-mail?' -> 'full_name' / 'e_mail'."""
    key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key.strip())
    key = re.sub(r"[^a-z0-9]+", "_", key.lower())
    return key.strip("_")


def parse_platform(value: str | None) -> SocialPlatform | None:
    if not value:
        return None
    return PLATFORM_ALIASES.get(normalize_key(value))


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):  # Meta field_data values, multi-select answers
        value = ", ".join(str(v) for v in value if v not in (None, ""))
    text = str(value).strip()
    return text or None


def _strip_meta_prefix(value: str | None, prefix: str) -> str | None:
    """Meta's CSV export writes 'p:+15551234' for phones and 'l:123' for lead ids."""
    if value and value.startswith(prefix):
        return value[len(prefix):].strip() or None
    return value


def _clean_email(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError:
        return None


def _humanize(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


@dataclass
class ParsedLead:
    name: str
    email: str | None
    phone: str | None
    company_name: str | None
    social_handle: str | None
    social_platform: SocialPlatform | None
    external_id: str | None
    score: int | None
    source: LeadSource | None
    extras: dict[str, str] = field(default_factory=dict)


def parse_row(raw: dict, default_platform: SocialPlatform | None = None) -> ParsedLead:
    """Map one loosely-shaped record onto lead fields. Raises ValueError when it can't be a lead."""
    values: dict[str, str] = {}
    labels: dict[str, str] = {}
    for key, value in raw.items():
        if key is None:
            continue
        if isinstance(value, dict):
            continue
        text = _text(value)
        if text is None:
            continue
        norm = normalize_key(str(key))
        if norm and norm not in values:
            values[norm] = text
            labels[norm] = str(key).strip()

    def pick(target: str) -> str | None:
        return next((values[a] for a in FIELD_ALIASES[target] if a in values), None)

    first, last = pick("first_name"), pick("last_name")
    raw_email = pick("email")
    email = _clean_email(raw_email)
    phone = _strip_meta_prefix(pick("phone"), "p:")
    handle = pick("social_handle")
    name = pick("name") or " ".join(part for part in (first, last) if part) or None
    name = name or (email.split("@")[0] if email else None) or handle or phone
    if not name:
        raise ValueError("No name, email, phone or handle")

    score: int | None = None
    if (raw_score := pick("score")) is not None:
        try:
            score = max(0, min(100, round(float(raw_score))))
        except ValueError:
            score = None
    source = None
    if raw_source := pick("source"):
        try:
            source = LeadSource(normalize_key(raw_source))
        except ValueError:
            source = None

    extras = {
        labels[key]: value
        for key, value in values.items()
        if key not in _MAPPED_COLUMNS and key not in IGNORED_EXTRAS
    }
    if raw_email and not email:
        extras["Email (invalid)"] = raw_email

    return ParsedLead(
        name=name[:200],
        email=email[:255] if email else None,
        phone=phone[:50] if phone else None,
        company_name=(pick("company_name") or "")[:255] or None,
        social_handle=handle[:255] if handle else None,
        social_platform=parse_platform(pick("platform")) or default_platform,
        external_id=(_strip_meta_prefix(pick("external_id"), "l:") or "")[:100] or None,
        score=score,
        source=source,
        extras=extras,
    )


def parse_csv(text: str) -> tuple[list[str], list[dict]]:
    """Header + rows of a CSV/TSV export (comma, tab or semicolon separated)."""
    text = text.lstrip("﻿")
    first_line = text.split("\n", 1)[0]
    delimiter = max(",\t;", key=first_line.count)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    columns = [c.strip() for c in (reader.fieldnames or []) if c and c.strip()]
    if not columns:
        raise ValueError("The file has no header row")
    rows = [row for row in reader if any((v or "").strip() for k, v in row.items() if k is not None)]
    if not rows:
        raise ValueError("The file has no data rows")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"The file has {len(rows)} rows; import at most {MAX_ROWS} at a time")
    return columns, rows


def _note_body(parsed: ParsedLead, via: str) -> str:
    lines = [f"Imported from {via}."]
    if parsed.extras:
        lines += ["", "Form answers and details:"]
        lines += [f"• {_humanize(key) if '_' in key else key}: {value}" for key, value in parsed.extras.items()]
    return "\n".join(lines)


@dataclass
class ImportContext:
    """Who/what an import is for."""

    actor: Profile | None  # None for webhooks (no signed-in user)
    owner_id: uuid.UUID | None
    default_score: int = 0
    default_platform: SocialPlatform | None = None
    integration: LeadIntegration | None = None
    via: str = "an import"  # shown in the note, e.g. "Instagram (Spring campaign)"
    channel: str = "csv"  # audit detail: csv / webhook / meta
    notify_each: bool = True  # False for bulk CSV imports: the caller sends one summary notification


def import_rows(db: Session, rows: list[dict], ctx: ImportContext, *, dry_run: bool = False) -> dict:
    """Create leads from `rows`. Adds to the session; the caller commits. Returns an ImportResult dict."""
    result: dict = {"created": 0, "skipped": 0, "failed": 0, "lead_ids": [], "issues": [], "preview": []}
    seen_emails: set[str] = set()
    seen_ids: set[tuple[str | None, str]] = set()

    def issue(index: int, name: str | None, reason: str, kind: str) -> None:
        result[kind] += 1
        if len(result["issues"]) < MAX_ISSUES:
            result["issues"].append({"row": index, "name": name, "reason": reason})

    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            issue(index, None, "Not an object", "failed")
            continue
        try:
            parsed = parse_row(raw, ctx.default_platform)
        except ValueError as exc:
            issue(index, None, str(exc), "failed")
            continue

        platform = parsed.social_platform
        id_key = (platform, parsed.external_id) if parsed.external_id else None
        if id_key and (id_key in seen_ids or _external_id_exists(db, platform, parsed.external_id)):
            issue(index, parsed.name, "Already imported", "skipped")
            continue
        email_key = parsed.email.lower() if parsed.email else None
        if email_key and (email_key in seen_emails or _email_exists(db, email_key)):
            issue(index, parsed.name, "A lead with this email already exists", "skipped")
            continue
        if id_key:
            seen_ids.add(id_key)
        if email_key:
            seen_emails.add(email_key)

        if dry_run:
            result["created"] += 1
            if len(result["preview"]) < PREVIEW_ROWS:
                result["preview"].append(
                    {
                        "name": parsed.name,
                        "email": parsed.email,
                        "phone": parsed.phone,
                        "company_name": parsed.company_name,
                        "social_platform": platform,
                        "social_handle": parsed.social_handle,
                    }
                )
            continue

        lead = _create_lead(db, parsed, ctx)
        if lead is None:  # lost a race with a parallel delivery of the same lead
            issue(index, parsed.name, "Already imported", "skipped")
            continue
        result["created"] += 1
        result["lead_ids"].append(lead.id)

    if ctx.integration is not None and result["created"] and not dry_run:
        ctx.integration.leads_imported += result["created"]
        ctx.integration.last_lead_at = datetime.now(UTC)
    return result


def _external_id_exists(db: Session, platform: SocialPlatform | None, external_id: str) -> bool:
    platform_match = Lead.social_platform.is_(None) if platform is None else Lead.social_platform == platform
    return db.scalar(select(Lead.id).where(platform_match, Lead.external_id == external_id).limit(1)) is not None


def _email_exists(db: Session, email: str) -> bool:
    return db.scalar(select(Lead.id).where(func.lower(Lead.email) == email).limit(1)) is not None


def _create_lead(db: Session, parsed: ParsedLead, ctx: ImportContext) -> Lead | None:
    platform = parsed.social_platform
    if platform is not None:
        source = LeadSource.SOCIAL_MEDIA
    else:
        source = parsed.source or LeadSource.OTHER
    lead = Lead(
        name=parsed.name,
        email=parsed.email,
        phone=parsed.phone,
        company_name=parsed.company_name,
        source=source,
        status=LeadStatus.NEW,
        score=parsed.score if parsed.score is not None else ctx.default_score,
        owner_id=ctx.owner_id,
        created_by_id=ctx.actor.id if ctx.actor else None,
        social_platform=platform,
        social_handle=parsed.social_handle,
        external_id=parsed.external_id,
        integration_id=ctx.integration.id if ctx.integration else None,
    )
    try:
        with db.begin_nested():
            db.add(lead)
            db.flush()
    except IntegrityError:
        return None

    db.add(Note(body=_note_body(parsed, ctx.via), owner_id=ctx.owner_id, lead_id=lead.id))
    audit.record(
        db,
        ctx.actor,
        "lead.imported",
        "lead",
        lead.id,
        name=lead.name,
        platform=platform,
        channel=ctx.channel,
        integration_id=ctx.integration.id if ctx.integration else None,
    )
    if not ctx.notify_each:
        return lead
    label = PLATFORM_LABELS[platform] if platform else "imported"
    notifications.notify(
        db,
        user_id=lead.owner_id,
        type=NotificationType.LEAD_ASSIGNED,
        title=f"New {label} lead: {lead.name}",
        message=f"“{lead.name}” came in via {ctx.via} and was assigned to you.",
        entity_type="lead",
        entity_id=lead.id,
        actor=ctx.actor,
    )
    return lead


def integration_owner(db: Session, integration: LeadIntegration) -> uuid.UUID | None:
    """Owner for leads from an integration: its default owner, else whoever set it up (if still active)."""
    for user_id in (integration.default_owner_id, integration.created_by_id):
        if user_id and (profile := db.get(Profile, user_id)) is not None and profile.is_active:
            return user_id
    return None


def integration_context(db: Session, integration: LeadIntegration, channel: str) -> ImportContext:
    platform = SocialPlatform(integration.platform)
    return ImportContext(
        actor=None,
        owner_id=integration_owner(db, integration),
        default_score=integration.default_score,
        default_platform=platform,
        integration=integration,
        via=f"{PLATFORM_LABELS[platform]} ({integration.name})",
        channel=channel,
    )
