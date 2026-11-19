import csv
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_manager
from app.dependencies.pagination import ListParams, list_params
from app.models import Lead, Profile
from app.models.enums import LeadSource, LeadStatus, NotificationType, SocialPlatform
from app.schemas.common import Page
from app.schemas.lead import LeadConvert, LeadConvertResult, LeadCreate, LeadRead, LeadUpdate
from app.schemas.lead_integration import CsvImport, ImportResult
from app.services import audit, notifications
from app.services import lead_import as importer
from app.services import leads as lead_service
from app.services.permissions import check_owner_change, ensure_can_edit, owner_for_create
from app.utils.query import apply_sort, get_or_404, paginate, search_filter

router = APIRouter(prefix="/leads", tags=["leads"])

SORTABLE = {
    "name": Lead.name,
    "score": Lead.score,
    "status": Lead.status,
    "source": Lead.source,
    "created_at": Lead.created_at,
    "updated_at": Lead.updated_at,
}


@router.get("", response_model=Page[LeadRead])
def list_leads(
    params: ListParams = Depends(list_params),
    status_filter: LeadStatus | None = Query(None, alias="status"),
    source: LeadSource | None = None,
    social_platform: SocialPlatform | None = None,
    owner_id: uuid.UUID | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Lead)
    if params.search:
        stmt = stmt.where(search_filter(params.search, Lead.name, Lead.email, Lead.company_name, Lead.phone, Lead.social_handle))
    if status_filter:
        stmt = stmt.where(Lead.status == status_filter)
    if source:
        stmt = stmt.where(Lead.source == source)
    if social_platform:
        stmt = stmt.where(Lead.social_platform == social_platform)
    if owner_id:
        stmt = stmt.where(Lead.owner_id == owner_id)
    if min_score is not None:
        stmt = stmt.where(Lead.score >= min_score)
    stmt = apply_sort(stmt, params, SORTABLE, default="created_at")
    return paginate(db, stmt, params)


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.status == LeadStatus.CONVERTED:
        raise bad_request("Use the convert action to convert a lead")
    lead = Lead(
        **payload.model_dump(exclude={"owner_id"}),
        owner_id=owner_for_create(db, user, payload.owner_id),
        created_by_id=user.id,
    )
    db.add(lead)
    db.flush()
    audit.record(db, user, "lead.created", "lead", lead.id, name=lead.name)
    notifications.notify_assignment(db, user, lead, "lead", NotificationType.LEAD_ASSIGNED)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/import", response_model=ImportResult)
def import_leads(payload: CsvImport, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bulk-create leads from a CSV/TSV export (Facebook, Instagram, LinkedIn, TikTok lead forms, ...).
    `dry_run` validates and previews without saving."""
    owner_id = owner_for_create(db, user, payload.owner_id)
    try:
        columns, rows = importer.parse_csv(payload.csv_text)
    except (ValueError, csv.Error) as exc:
        raise bad_request(f"Couldn't read the file: {exc}")
    label = importer.PLATFORM_LABELS[payload.platform] + " " if payload.platform else ""
    ctx = importer.ImportContext(
        actor=user,
        owner_id=owner_id,
        default_score=payload.score,
        default_platform=payload.platform,
        via=f"a {label}CSV import by {user.full_name}",
        channel="csv",
        notify_each=False,
    )
    result = importer.import_rows(db, rows, ctx, dry_run=payload.dry_run)
    result["columns"] = columns
    if payload.dry_run:
        return result
    if result["created"]:
        count = result["created"]
        notifications.notify(
            db,
            user_id=owner_id,
            type=NotificationType.LEAD_ASSIGNED,
            title=f"{count} imported lead{'s' if count != 1 else ''} assigned to you",
            message=f"{user.full_name} imported {count} {label}lead{'s' if count != 1 else ''} and assigned them to you.",
            entity_type="lead",
            entity_id=result["lead_ids"][0],
            actor=user,
        )
    db.commit()
    return result


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: uuid.UUID, _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_or_404(db, Lead, lead_id)


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = get_or_404(db, Lead, lead_id)
    ensure_can_edit(user, lead)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] != lead.status:
        if data["status"] == LeadStatus.CONVERTED:
            raise bad_request("Use the convert action to convert a lead")
        if lead.status == LeadStatus.CONVERTED:
            raise bad_request("A converted lead's status can't be changed")
    if "owner_id" in data:
        check_owner_change(db, user, lead, data["owner_id"])
    for field in ("name", "source", "status", "score"):
        if field in data and data[field] is None:
            data.pop(field)
    if changes := audit.apply_changes(lead, data):
        audit.record(db, user, "lead.updated", "lead", lead.id, name=lead.name, changes=changes)
        if "owner_id" in changes:
            notifications.notify_assignment(db, user, lead, "lead", NotificationType.LEAD_ASSIGNED)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/convert", response_model=LeadConvertResult)
def convert_lead(
    lead_id: uuid.UUID,
    payload: LeadConvert,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = get_or_404(db, Lead, lead_id)
    ensure_can_edit(user, lead)
    result = lead_service.convert_lead(db, user, lead, payload)
    audit.record(
        db,
        user,
        "lead.converted",
        "lead",
        lead.id,
        name=lead.name,
        contact_id=result["contact"].id,
        company_id=result["company"].id if result["company"] else None,
        deal_id=result["deal"].id if result["deal"] else None,
    )
    db.commit()
    return {
        "lead": result["lead"],
        "contact_id": result["contact"].id,
        "company_id": result["company"].id if result["company"] else None,
        "deal_id": result["deal"].id if result["deal"] else None,
    }


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: uuid.UUID, user: Profile = Depends(require_manager), db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id)
    audit.record(db, user, "lead.deleted", "lead", lead.id, name=lead.name)
    db.delete(lead)
    db.commit()
