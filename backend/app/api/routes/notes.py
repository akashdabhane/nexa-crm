import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import ListParams, list_params
from app.models import Note, Profile
from app.schemas.common import Page
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.services.permissions import ensure_can_edit
from app.services.related import validate_related
from app.utils.query import apply_sort, get_or_404, paginate, search_filter

router = APIRouter(prefix="/notes", tags=["notes"])

SORTABLE = {"created_at": Note.created_at, "updated_at": Note.updated_at}


@router.get("", response_model=Page[NoteRead])
def list_notes(
    params: ListParams = Depends(list_params),
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
    deal_id: uuid.UUID | None = None,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Note)
    if params.search:
        stmt = stmt.where(search_filter(params.search, Note.body))
    for column, value in {
        Note.contact_id: contact_id,
        Note.company_id: company_id,
        Note.lead_id: lead_id,
        Note.deal_id: deal_id,
    }.items():
        if value is not None:
            stmt = stmt.where(column == value)
    stmt = apply_sort(stmt, params, SORTABLE, default="created_at")
    return paginate(db, stmt, params)


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    validate_related(db, data)
    note = Note(**data, owner_id=user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = get_or_404(db, Note, note_id)
    ensure_can_edit(user, note)
    note.body = payload.body
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: uuid.UUID, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    note = get_or_404(db, Note, note_id)
    ensure_can_edit(user, note)
    db.delete(note)
    db.commit()
