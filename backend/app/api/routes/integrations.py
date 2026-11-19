"""Social media lead integrations.

Admin endpoints manage the connections. Two endpoints are public by design
(no Supabase token; the callers are Meta and automation tools):

- POST /integrations/webhooks/{token}: the integration's secret URL; any tool can send leads.
- GET/POST /integrations/meta/webhook: Meta's verification handshake and signed `leadgen` events.
"""

import json
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import bad_gateway, bad_request, forbidden, not_found, service_unavailable
from app.core.security import SecretError, decrypt_secret, encrypt_secret
from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models import LeadIntegration, Profile
from app.models.enums import IntegrationKind, SocialPlatform
from app.schemas.lead_integration import (
    ImportResult,
    IntegrationCreate,
    IntegrationRead,
    IntegrationSetup,
    IntegrationUpdate,
)
from app.services import audit, meta_leads
from app.services import lead_import as importer
from app.services.permissions import ensure_user_exists
from app.utils.query import get_or_404

logger = logging.getLogger("nexa_crm")

router = APIRouter(prefix="/integrations", tags=["integrations"])

MAX_WEBHOOK_LEADS = 100
META_PLATFORMS = (SocialPlatform.FACEBOOK, SocialPlatform.INSTAGRAM)


def _new_token() -> str:
    return secrets.token_urlsafe(32)


async def raw_body(request: Request) -> bytes:
    """The exact request bytes (Meta signs them). Async dependency; the endpoint itself stays sync."""
    return await request.body()


def _connect_meta(integration: LeadIntegration, page_id: str, token: str) -> None:
    """Validate the Page token, remember the Page name and subscribe the Page to leadgen webhooks."""
    try:
        page = meta_leads.get_page(page_id, token)
    except meta_leads.MetaError as exc:
        raise bad_request(f"Meta rejected the Page access token: {exc}")
    try:
        integration.access_token_encrypted = encrypt_secret(token)
    except SecretError as exc:
        raise service_unavailable(str(exc))
    integration.meta_page_id = page_id
    integration.meta_page_name = page.get("name")
    integration.last_error = None
    try:
        meta_leads.subscribe_page(page_id, token)
    except meta_leads.MetaError as exc:
        # Not fatal: "Sync now" still works, and the Page can be subscribed later.
        integration.last_error = f"Couldn't subscribe the Page to lead webhooks: {exc}"[:500]


@router.get("/setup", response_model=IntegrationSetup)
def get_setup(_: Profile = Depends(require_admin)):
    return {
        "meta_webhook_ready": bool(settings.meta_app_secret and settings.meta_verify_token),
        "token_storage_ready": bool(settings.integrations_secret),
    }


@router.get("", response_model=list[IntegrationRead])
def list_integrations(_: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(LeadIntegration).order_by(LeadIntegration.created_at)).unique().all()


@router.post("", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
def create_integration(payload: IntegrationCreate, user: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    if payload.default_owner_id:
        ensure_user_exists(db, payload.default_owner_id)
    integration = LeadIntegration(
        name=payload.name,
        kind=payload.kind,
        platform=payload.platform,
        is_active=payload.is_active,
        webhook_token=_new_token(),
        default_owner_id=payload.default_owner_id,
        default_score=payload.default_score,
        created_by_id=user.id,
    )
    if payload.kind == IntegrationKind.META_LEAD_ADS:
        if payload.platform not in META_PLATFORMS:
            integration.platform = SocialPlatform.FACEBOOK
        if not payload.meta_page_id or not payload.access_token:
            raise bad_request("Meta Lead Ads needs a Facebook Page ID and a Page access token")
        _connect_meta(integration, payload.meta_page_id, payload.access_token)
    db.add(integration)
    db.flush()
    audit.record(db, user, "integration.created", "integration", integration.id, name=integration.name, platform=integration.platform)
    db.commit()
    db.refresh(integration)
    return integration


@router.patch("/{integration_id}", response_model=IntegrationRead)
def update_integration(
    integration_id: uuid.UUID,
    payload: IntegrationUpdate,
    user: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    integration = get_or_404(db, LeadIntegration, integration_id, "Integration")
    data = payload.model_dump(exclude_unset=True)
    token = data.pop("access_token", None)
    page_id = data.pop("meta_page_id", None)
    if data.get("default_owner_id"):
        ensure_user_exists(db, data["default_owner_id"])
    for field in ("name", "platform", "is_active", "default_score"):
        if field in data and data[field] is None:
            data.pop(field)
    is_meta = integration.kind == IntegrationKind.META_LEAD_ADS
    if is_meta and data.get("platform") not in (None, *META_PLATFORMS):
        raise bad_request("A Meta Lead Ads integration is for Facebook or Instagram")
    changes = audit.apply_changes(integration, data)
    if is_meta and (token or (page_id and page_id != integration.meta_page_id)):
        if token is None:
            try:
                token = decrypt_secret(integration.access_token_encrypted or "")
            except SecretError as exc:
                raise bad_request(f"Enter the Page access token again ({exc})")
        _connect_meta(integration, page_id or integration.meta_page_id or "", token)
        changes["access_token"] = ["…", "…"]
    if changes:
        audit.record(db, user, "integration.updated", "integration", integration.id, name=integration.name, changes=changes)
    db.commit()
    db.refresh(integration)
    return integration


@router.post("/{integration_id}/rotate-token", response_model=IntegrationRead)
def rotate_webhook_token(integration_id: uuid.UUID, user: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    """Issue a new webhook URL; the old one stops working immediately."""
    integration = get_or_404(db, LeadIntegration, integration_id, "Integration")
    integration.webhook_token = _new_token()
    audit.record(db, user, "integration.token_rotated", "integration", integration.id, name=integration.name)
    db.commit()
    db.refresh(integration)
    return integration


@router.post("/{integration_id}/sync", response_model=ImportResult)
def sync_integration(integration_id: uuid.UUID, user: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    """Pull the Page's lead-form leads from Meta (new ones since the last sync; all on the first)."""
    integration = get_or_404(db, LeadIntegration, integration_id, "Integration")
    if integration.kind != IntegrationKind.META_LEAD_ADS or not integration.meta_page_id:
        raise bad_request("Only Meta Lead Ads integrations can be synced")
    try:
        token = decrypt_secret(integration.access_token_encrypted or "")
    except SecretError as exc:
        raise service_unavailable(str(exc))
    started = datetime.now(UTC)
    try:
        rows = [meta_leads.lead_to_row(lead) for lead in meta_leads.iter_page_leads(integration.meta_page_id, token, integration.last_synced_at)]
    except meta_leads.MetaError as exc:
        integration.last_error = str(exc)[:500]
        db.commit()
        raise bad_gateway(f"Meta: {exc}")
    ctx = _meta_context(db, integration)
    result = importer.import_rows(db, rows, ctx)
    integration.last_synced_at = started
    integration.last_error = None
    audit.record(db, user, "integration.synced", "integration", integration.id, name=integration.name, created=result["created"])
    db.commit()
    return result


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(integration_id: uuid.UUID, user: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    """Leads it imported stay; they just lose the link to the integration."""
    integration = get_or_404(db, LeadIntegration, integration_id, "Integration")
    audit.record(db, user, "integration.deleted", "integration", integration.id, name=integration.name)
    db.delete(integration)
    db.commit()


# --- Public endpoints --------------------------------------------------------


def _meta_context(db: Session, integration: LeadIntegration) -> importer.ImportContext:
    ctx = importer.integration_context(db, integration, channel="meta")
    ctx.via = f"Meta lead ads ({integration.meta_page_name or integration.name})"
    return ctx


@router.post("/webhooks/{token}", response_model=ImportResult)
def receive_webhook(
    token: str,
    payload: dict[str, Any] | list[Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Inbound leads for one integration. Body: a lead object, a list of them, or {"leads": [...]}.

    Recognized keys (any casing/spacing): full_name or first_name + last_name, email, phone,
    company, username/handle/profile_url, id (the platform's lead id), platform, score.
    Anything else is saved as a note on the lead.
    """
    integration = None
    if len(token) >= 20:
        integration = db.scalar(select(LeadIntegration).where(LeadIntegration.webhook_token == token))
    if integration is None:
        raise not_found("Integration")
    if not integration.is_active:
        raise forbidden("This integration is paused")
    if isinstance(payload, dict):
        leads = payload["leads"] if isinstance(payload.get("leads"), list) else [payload]
    else:
        leads = payload
    if not leads:
        raise bad_request("No leads in the request")
    if len(leads) > MAX_WEBHOOK_LEADS:
        raise bad_request(f"Send at most {MAX_WEBHOOK_LEADS} leads per request")
    result = importer.import_rows(db, leads, importer.integration_context(db, integration, channel="webhook"))
    db.commit()
    return result


@router.get("/meta/webhook", response_class=PlainTextResponse)
def verify_meta_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge", max_length=200),
):
    """Meta's one-time subscription check: echo the challenge if the verify token matches."""
    if not settings.meta_verify_token:
        raise service_unavailable("META_VERIFY_TOKEN is not configured")
    if mode != "subscribe" or not verify_token or not secrets.compare_digest(verify_token, settings.meta_verify_token):
        raise forbidden("Verification token mismatch")
    return challenge


@router.post("/meta/webhook")
def receive_meta_webhook(
    body: bytes = Depends(raw_body),
    signature: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db),
):
    """Signed `leadgen` events. Always answers 200 once the signature is valid, so Meta doesn't retry
    forever on a lead we can't fetch; failures are shown on the integration instead."""
    if not settings.meta_app_secret:
        raise service_unavailable("META_APP_SECRET is not configured")
    if not meta_leads.verify_signature(body, signature):
        raise forbidden("Invalid signature")
    try:
        event = json.loads(body or b"{}")
    except ValueError:
        raise bad_request("Invalid JSON")

    created = 0
    for entry in event.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "leadgen":
                continue
            value = change.get("value") or {}
            page_id, leadgen_id = str(value.get("page_id") or entry.get("id") or ""), str(value.get("leadgen_id") or "")
            if not page_id or not leadgen_id:
                continue
            integrations = db.scalars(
                select(LeadIntegration).where(
                    LeadIntegration.kind == IntegrationKind.META_LEAD_ADS,
                    LeadIntegration.meta_page_id == page_id,
                    LeadIntegration.is_active.is_(True),
                )
            ).unique().all()
            for integration in integrations:
                try:
                    token = decrypt_secret(integration.access_token_encrypted or "")
                    lead = meta_leads.get_lead(leadgen_id, token)
                except (SecretError, meta_leads.MetaError) as exc:
                    logger.warning("Meta lead %s for page %s failed: %s", leadgen_id, page_id, exc)
                    integration.last_error = f"Lead {leadgen_id}: {exc}"[:500]
                    continue
                result = importer.import_rows(db, [meta_leads.lead_to_row(lead)], _meta_context(db, integration))
                created += result["created"]
                if result["created"]:
                    integration.last_error = None
    db.commit()
    return {"received": True, "created": created}
