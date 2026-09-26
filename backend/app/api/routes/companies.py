import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_manager
from app.dependencies.pagination import ListParams, list_params
from app.models import Company, Contact, Deal, Profile
from app.models.enums import DealStatus
from app.schemas.common import EntityRef, Page
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services import audit
from app.services.permissions import check_owner_change, ensure_can_edit, owner_for_create
from app.utils.query import apply_sort, get_or_404, paginate, search_filter

router = APIRouter(prefix="/companies", tags=["companies"])

SORTABLE = {
    "name": Company.name,
    "industry": Company.industry,
    "employee_count": Company.employee_count,
    "city": Company.city,
    "created_at": Company.created_at,
    "updated_at": Company.updated_at,
}


def _to_read(db: Session, companies: list[Company]) -> list[CompanyRead]:
    """Attach related-record counts with one grouped query per relation."""
    ids = [company.id for company in companies]
    contact_counts: dict = {}
    deal_stats: dict = {}
    if ids:
        contact_counts = dict(
            db.execute(
                select(Contact.company_id, func.count())
                .where(Contact.company_id.in_(ids))
                .group_by(Contact.company_id)
            ).all()
        )
        open_value = func.coalesce(func.sum(Deal.value).filter(Deal.status == DealStatus.OPEN), 0)
        deal_stats = {
            row.company_id: row
            for row in db.execute(
                select(Deal.company_id, func.count().label("count"), open_value.label("open_value"))
                .where(Deal.company_id.in_(ids))
                .group_by(Deal.company_id)
            )
        }
    result = []
    for company in companies:
        stats = deal_stats.get(company.id)
        result.append(
            CompanyRead.model_validate(company).model_copy(
                update={
                    "contact_count": contact_counts.get(company.id, 0),
                    "deal_count": stats.count if stats else 0,
                    "open_deal_value": float(stats.open_value) if stats else 0,
                }
            )
        )
    return result


@router.get("", response_model=Page[CompanyRead])
def list_companies(
    params: ListParams = Depends(list_params),
    industry: str | None = None,
    country: str | None = None,
    owner_id: uuid.UUID | None = None,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Company)
    if params.search:
        stmt = stmt.where(search_filter(params.search, Company.name, Company.industry, Company.email, Company.city))
    if industry:
        stmt = stmt.where(Company.industry == industry)
    if country:
        stmt = stmt.where(Company.country == country)
    if owner_id:
        stmt = stmt.where(Company.owner_id == owner_id)
    stmt = apply_sort(stmt, params, SORTABLE, default="created_at")

    page = paginate(db, stmt, params)
    page["items"] = _to_read(db, page["items"])
    return page


@router.get("/industries", response_model=list[str])
def list_industries(_: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    """Distinct industries, for the filter dropdown."""
    return db.scalars(
        select(Company.industry).where(Company.industry.is_not(None)).distinct().order_by(Company.industry)
    ).all()


@router.get("/options", response_model=list[EntityRef])
def company_options(
    search: str | None = Query(None, max_length=100),
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lightweight id/name list for select inputs."""
    stmt = select(Company.id, Company.name).order_by(Company.name).limit(50)
    if search:
        stmt = stmt.where(Company.name.ilike(f"%{search}%"))
    return [{"id": row.id, "name": row.name} for row in db.execute(stmt)]


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude={"owner_id"})
    company = Company(**data, owner_id=owner_for_create(db, user, payload.owner_id), created_by_id=user.id)
    db.add(company)
    db.flush()
    audit.record(db, user, "company.created", "company", company.id, name=company.name)
    db.commit()
    db.refresh(company)
    return _to_read(db, [company])[0]


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: uuid.UUID, _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return _to_read(db, [get_or_404(db, Company, company_id)])[0]


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = get_or_404(db, Company, company_id)
    ensure_can_edit(user, company)
    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data:
        check_owner_change(db, user, company, data["owner_id"])
    if "name" in data and data["name"] is None:
        data.pop("name")
    if changes := audit.apply_changes(company, data):
        audit.record(db, user, "company.updated", "company", company.id, name=company.name, changes=changes)
    db.commit()
    db.refresh(company)
    return _to_read(db, [company])[0]


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: uuid.UUID,
    user: Profile = Depends(require_manager),
    db: Session = Depends(get_db),
):
    company = get_or_404(db, Company, company_id)
    audit.record(db, user, "company.deleted", "company", company.id, name=company.name)
    db.delete(company)
    db.commit()
