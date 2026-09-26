from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_manager
from app.models import Activity, Profile, Task
from app.models.enums import TaskStatus
from app.schemas.activity import ActivityRead
from app.schemas.task import TaskRead
from app.services import reports
from app.services.reports import DateRange

router = APIRouter(tags=["reports"])


def date_range(start_date: date | None = None, end_date: date | None = None) -> DateRange:
    if start_date and end_date and start_date > end_date:
        raise bad_request("start_date must be before end_date")
    return DateRange(start_date, end_date)


@router.get("/dashboard/summary")
def dashboard_summary(user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    """KPIs, charts data, recent activity and the current user's upcoming tasks."""
    recent_activities = db.scalars(select(Activity).order_by(Activity.occurred_at.desc()).limit(8)).all()
    upcoming_tasks = db.scalars(
        select(Task)
        .where(
            Task.owner_id == user.id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            Task.due_date <= date.today() + timedelta(days=14),
        )
        .order_by(Task.due_date.asc().nulls_last())
        .limit(8)
    ).all()
    last_6_months = DateRange(start=(date.today().replace(day=1) - timedelta(days=150)).replace(day=1))
    return {
        "totals": reports.dashboard_summary(db),
        "pipeline": reports.pipeline(db, DateRange()),
        "revenue": reports.revenue_by_month(db, last_6_months),
        "lead_sources": reports.lead_sources(db, DateRange()),
        "recent_activities": [ActivityRead.model_validate(a) for a in recent_activities],
        "upcoming_tasks": [TaskRead.model_validate(t) for t in upcoming_tasks],
    }


@router.get("/reports/lead-conversion")
def lead_conversion(period: DateRange = Depends(date_range), _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.lead_conversion(db, period)


@router.get("/reports/pipeline")
def pipeline(period: DateRange = Depends(date_range), _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.pipeline(db, period)


@router.get("/reports/revenue")
def revenue(period: DateRange = Depends(date_range), _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.revenue_by_month(db, period)


@router.get("/reports/win-loss")
def win_loss(period: DateRange = Depends(date_range), _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.win_loss(db, period)


@router.get("/reports/rep-performance")
def rep_performance(period: DateRange = Depends(date_range), _: Profile = Depends(require_manager), db: Session = Depends(get_db)):
    return reports.rep_performance(db, period)


@router.get("/reports/lead-sources")
def lead_sources(period: DateRange = Depends(date_range), _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return reports.lead_sources(db, period)
