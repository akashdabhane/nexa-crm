import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_manager
from app.dependencies.pagination import ListParams, list_params
from app.models import Deal, Profile
from app.models.enums import DealStatus, NotificationType, StageType
from app.schemas.common import Page
from app.schemas.deal import DealBoard, DealCreate, DealRead, DealStageUpdate, DealUpdate
from app.services import audit, notifications
from app.services import deals as deal_service
from app.services import pipelines
from app.services.permissions import check_owner_change, ensure_can_edit, owner_for_create
from app.utils.query import apply_sort, get_or_404, paginate, search_filter

router = APIRouter(prefix="/deals", tags=["deals"])

SORTABLE = {
    "name": Deal.name,
    "value": Deal.value,
    "probability": Deal.probability,
    "expected_close_date": Deal.expected_close_date,
    "status": Deal.status,
    "created_at": Deal.created_at,
    "updated_at": Deal.updated_at,
    "closed_at": Deal.closed_at,
}

# Won/lost columns only show recent deals so the board stays readable.
CLOSED_DEALS_ON_BOARD = 15


def _filtered(
    stmt,
    search: str | None,
    owner_id: uuid.UUID | None,
    company_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
):
    if search:
        stmt = stmt.where(search_filter(search, Deal.name, Deal.description))
    if owner_id:
        stmt = stmt.where(Deal.owner_id == owner_id)
    if company_id:
        stmt = stmt.where(Deal.company_id == company_id)
    if contact_id:
        stmt = stmt.where(Deal.contact_id == contact_id)
    return stmt


def _move(db: Session, user: Profile, deal: Deal, stage_id: uuid.UUID) -> None:
    """Change stage + audit trail + won/lost notifications."""
    from_stage = deal.stage.name
    was_open = deal.status == DealStatus.OPEN
    deal_service.apply_stage(deal, pipelines.get_stage(db, stage_id, deal.pipeline_id))
    audit.record(
        db, user, "deal.stage_changed", "deal", deal.id, name=deal.name, **{"from": from_stage, "to": deal.stage.name}
    )
    if was_open and deal.status != DealStatus.OPEN:
        notifications.notify_deal_closed(db, user, deal)


@router.get("", response_model=Page[DealRead])
def list_deals(
    params: ListParams = Depends(list_params),
    pipeline_id: uuid.UUID | None = None,
    stage_id: uuid.UUID | None = None,
    status_filter: DealStatus | None = Query(None, alias="status"),
    owner_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    close_from: date | None = None,
    close_to: date | None = None,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = _filtered(select(Deal), params.search, owner_id, company_id, contact_id)
    if pipeline_id:
        stmt = stmt.where(Deal.pipeline_id == pipeline_id)
    if stage_id:
        stmt = stmt.where(Deal.stage_id == stage_id)
    if status_filter:
        stmt = stmt.where(Deal.status == status_filter)
    if close_from:
        stmt = stmt.where(Deal.expected_close_date >= close_from)
    if close_to:
        stmt = stmt.where(Deal.expected_close_date <= close_to)
    stmt = apply_sort(stmt, params, SORTABLE, default="created_at")
    return paginate(db, stmt, params)


@router.get("/board", response_model=DealBoard)
def deal_board(
    pipeline_id: uuid.UUID | None = None,
    search: str | None = Query(None, max_length=100),
    owner_id: uuid.UUID | None = None,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deals grouped by stage for the Kanban board."""
    pipeline = pipelines.get_pipeline(db, pipeline_id)
    db.commit()  # persists the default pipeline if it was just created

    columns = []
    for stage in pipeline.stages:
        base = _filtered(select(Deal).where(Deal.stage_id == stage.id), search, owner_id)
        rows = base.subquery()
        count, total = db.execute(select(func.count(), func.coalesce(func.sum(rows.c.value), 0))).one()
        stmt = base.order_by(Deal.updated_at.desc())
        if stage.stage_type != StageType.OPEN:
            stmt = stmt.limit(CLOSED_DEALS_ON_BOARD)
        columns.append(
            {"stage": stage, "deals": db.scalars(stmt).unique().all(), "count": count, "total_value": total}
        )
    return {"pipeline_id": pipeline.id, "columns": columns}


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
def create_deal(payload: DealCreate, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    deal = deal_service.create_deal(
        db,
        user=user,
        owner_id=owner_for_create(db, user, payload.owner_id),
        **payload.model_dump(exclude={"owner_id"}),
    )
    audit.record(db, user, "deal.created", "deal", deal.id, name=deal.name, value=deal.value, stage=deal.stage.name)
    notifications.notify_assignment(db, user, deal, "deal", NotificationType.DEAL_ASSIGNED)
    if deal.status != DealStatus.OPEN:
        notifications.notify_deal_closed(db, user, deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.get("/{deal_id}", response_model=DealRead)
def get_deal(deal_id: uuid.UUID, _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_or_404(db, Deal, deal_id)


@router.patch("/{deal_id}", response_model=DealRead)
def update_deal(
    deal_id: uuid.UUID,
    payload: DealUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deal = get_or_404(db, Deal, deal_id)
    ensure_can_edit(user, deal)
    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data:
        check_owner_change(db, user, deal, data["owner_id"])
    deal_service.validate_links(db, data.get("company_id"), data.get("contact_id"))

    stage_id = data.pop("stage_id", None)
    if stage_id and stage_id != deal.stage_id:
        _move(db, user, deal, stage_id)
    for field in ("name", "value", "currency", "probability"):
        if field in data and data[field] is None:
            data.pop(field)
    if changes := audit.apply_changes(deal, data):
        audit.record(db, user, "deal.updated", "deal", deal.id, name=deal.name, changes=changes)
        if "owner_id" in changes:
            notifications.notify_assignment(db, user, deal, "deal", NotificationType.DEAL_ASSIGNED)
    db.commit()
    db.refresh(deal)
    return deal


@router.patch("/{deal_id}/stage", response_model=DealRead)
def move_deal(
    deal_id: uuid.UUID,
    payload: DealStageUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Move a deal to another stage (Kanban drag-and-drop)."""
    deal = get_or_404(db, Deal, deal_id)
    ensure_can_edit(user, deal)
    if payload.stage_id != deal.stage_id:
        _move(db, user, deal, payload.stage_id)
        db.commit()
        db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(deal_id: uuid.UUID, user: Profile = Depends(require_manager), db: Session = Depends(get_db)):
    deal = get_or_404(db, Deal, deal_id)
    audit.record(db, user, "deal.deleted", "deal", deal.id, name=deal.name, value=deal.value)
    db.delete(deal)
    db.commit()
