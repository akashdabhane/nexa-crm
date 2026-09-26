import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_manager
from app.dependencies.pagination import ListParams, list_params
from app.models import AuditLog, Profile
from app.schemas.common import Page
from app.schemas.notification import AuditLogRead
from app.services.reports import DateRange
from app.utils.query import apply_sort, paginate, search_filter

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogRead])
def list_audit_logs(
    params: ListParams = Depends(list_params),
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    _: Profile = Depends(require_manager),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).where(DateRange(start_date, end_date).filter(AuditLog.created_at))
    if params.search:
        stmt = stmt.where(search_filter(params.search, AuditLog.action, AuditLog.details["name"].astext))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = apply_sort(stmt, params, {"created_at": AuditLog.created_at}, default="created_at")
    return paginate(db, stmt, params)
