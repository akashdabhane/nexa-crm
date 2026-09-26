import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import ListParams, list_params
from app.models import Activity, Profile
from app.models.enums import ActivityType
from app.schemas.activity import ActivityCreate, ActivityRead, ActivityUpdate
from app.schemas.common import Page
from app.services.permissions import ensure_can_edit
from app.services.related import validate_related
from app.utils.query import apply_sort, get_or_404, paginate, search_filter

router = APIRouter(prefix="/activities", tags=["activities"])

SORTABLE = {"occurred_at": Activity.occurred_at, "type": Activity.type, "created_at": Activity.created_at}


def day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


@router.get("", response_model=Page[ActivityRead])
def list_activities(
    params: ListParams = Depends(list_params),
    type: ActivityType | None = None,
    owner_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
    deal_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Activity)
    if params.search:
        stmt = stmt.where(search_filter(params.search, Activity.subject, Activity.description))
    filters = {
        Activity.type: type,
        Activity.owner_id: owner_id,
        Activity.contact_id: contact_id,
        Activity.company_id: company_id,
        Activity.lead_id: lead_id,
        Activity.deal_id: deal_id,
    }
    for column, value in filters.items():
        if value is not None:
            stmt = stmt.where(column == value)
    if date_from:
        stmt = stmt.where(Activity.occurred_at >= day_start(date_from))
    if date_to:
        stmt = stmt.where(Activity.occurred_at < day_start(date_to) + timedelta(days=1))
    stmt = apply_sort(stmt, params, SORTABLE, default="occurred_at")
    return paginate(db, stmt, params)


@router.post("", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreate, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    validate_related(db, data)
    activity = Activity(**data, owner_id=user.id)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.patch("/{activity_id}", response_model=ActivityRead)
def update_activity(
    activity_id: uuid.UUID,
    payload: ActivityUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    activity = get_or_404(db, Activity, activity_id)
    ensure_can_edit(user, activity)
    data = payload.model_dump(exclude_unset=True)
    validate_related(db, data)
    for field in ("type", "subject", "occurred_at"):
        if field in data and data[field] is None:
            data.pop(field)
    for field, value in data.items():
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: uuid.UUID, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    activity = get_or_404(db, Activity, activity_id)
    ensure_can_edit(user, activity)  # authors can delete their own entries
    db.delete(activity)
    db.commit()
