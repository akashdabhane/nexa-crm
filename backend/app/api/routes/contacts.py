import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_manager
from app.dependencies.pagination import ListParams, list_params
from app.models import Company, Contact, Profile
from app.models.enums import ContactStatus
from app.schemas.common import EntityRef, Page
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.services import audit
from app.services.permissions import check_owner_change, ensure_can_edit, owner_for_create
from app.utils.query import apply_sort, get_or_404, paginate, search_filter

router = APIRouter(prefix="/contacts", tags=["contacts"])

SORTABLE = {
    "first_name": Contact.first_name,
    "last_name": Contact.last_name,
    "email": Contact.email,
    "status": Contact.status,
    "created_at": Contact.created_at,
    "updated_at": Contact.updated_at,
}


def _ensure_company(db: Session, company_id: uuid.UUID | None) -> None:
    if company_id is not None and db.get(Company, company_id) is None:
        raise bad_request("Company does not exist")


@router.get("", response_model=Page[ContactRead])
def list_contacts(
    params: ListParams = Depends(list_params),
    status_filter: ContactStatus | None = Query(None, alias="status"),
    company_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    tag: str | None = None,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Contact)
    if params.search:
        full_name = func.concat(Contact.first_name, " ", Contact.last_name)
        stmt = stmt.where(
            search_filter(params.search, full_name, Contact.email, Contact.phone, Contact.job_title)
        )
    if status_filter:
        stmt = stmt.where(Contact.status == status_filter)
    if company_id:
        stmt = stmt.where(Contact.company_id == company_id)
    if owner_id:
        stmt = stmt.where(Contact.owner_id == owner_id)
    if tag:
        stmt = stmt.where(Contact.tags.any(tag))
    stmt = apply_sort(stmt, params, SORTABLE, default="created_at")
    return paginate(db, stmt, params)


@router.get("/tags", response_model=list[str])
def list_tags(_: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every tag in use, for the tag filter."""
    tag = func.unnest(Contact.tags).label("tag")
    return db.scalars(select(tag).distinct().order_by(tag)).all()


@router.get("/options", response_model=list[EntityRef])
def contact_options(
    search: str | None = Query(None, max_length=100),
    company_id: uuid.UUID | None = None,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lightweight id/name list for select inputs."""
    stmt = select(Contact).order_by(Contact.first_name, Contact.last_name).limit(50)
    if search:
        stmt = stmt.where(search_filter(search, func.concat(Contact.first_name, " ", Contact.last_name), Contact.email))
    if company_id:
        stmt = stmt.where(Contact.company_id == company_id)
    return [{"id": contact.id, "name": contact.full_name} for contact in db.scalars(stmt).unique()]


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_company(db, payload.company_id)
    contact = Contact(
        **payload.model_dump(exclude={"owner_id"}),
        owner_id=owner_for_create(db, user, payload.owner_id),
        created_by_id=user.id,
    )
    db.add(contact)
    db.flush()
    audit.record(db, user, "contact.created", "contact", contact.id, name=contact.full_name)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: uuid.UUID, _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_or_404(db, Contact, contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = get_or_404(db, Contact, contact_id)
    ensure_can_edit(user, contact)
    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data:
        check_owner_change(db, user, contact, data["owner_id"])
    if "company_id" in data:
        _ensure_company(db, data["company_id"])
    # Required columns can't be cleared.
    for required in ("first_name", "status", "tags"):
        if required in data and data[required] is None:
            data.pop(required)
    if changes := audit.apply_changes(contact, data):
        audit.record(db, user, "contact.updated", "contact", contact.id, name=contact.full_name, changes=changes)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: uuid.UUID,
    user: Profile = Depends(require_manager),
    db: Session = Depends(get_db),
):
    contact = get_or_404(db, Contact, contact_id)
    audit.record(db, user, "contact.deleted", "contact", contact.id, name=contact.full_name)
    db.delete(contact)
    db.commit()
