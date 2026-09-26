import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import Activity, Contact, Note, Profile
from app.schemas.activity import ActivityRead
from app.schemas.note import NoteRead

router = APIRouter(prefix="/timeline", tags=["timeline"])


class TimelineItem(BaseModel):
    kind: Literal["activity", "note"]
    occurred_at: datetime
    activity: ActivityRead | None = None
    note: NoteRead | None = None


@router.get("", response_model=list[TimelineItem])
def get_timeline(
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
    deal_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=200),
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activities and notes for one record, newest first.

    A company's timeline also includes entries logged against its contacts.
    """
    if sum(value is not None for value in (contact_id, company_id, lead_id, deal_id)) != 1:
        raise bad_request("Pass exactly one of contact_id, company_id, lead_id or deal_id")

    def condition(model):
        if contact_id:
            return model.contact_id == contact_id
        if lead_id:
            return model.lead_id == lead_id
        if deal_id:
            return model.deal_id == deal_id
        company_contacts = select(Contact.id).where(Contact.company_id == company_id)
        return or_(model.company_id == company_id, model.contact_id.in_(company_contacts))

    activities = db.scalars(
        select(Activity).where(condition(Activity)).order_by(Activity.occurred_at.desc()).limit(limit)
    ).all()
    notes = db.scalars(select(Note).where(condition(Note)).order_by(Note.created_at.desc()).limit(limit)).all()

    items = [
        TimelineItem(kind="activity", occurred_at=a.occurred_at, activity=ActivityRead.model_validate(a))
        for a in activities
    ] + [TimelineItem(kind="note", occurred_at=n.created_at, note=NoteRead.model_validate(n)) for n in notes]
    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items[:limit]
