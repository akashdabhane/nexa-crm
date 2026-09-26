import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import ListParams, list_params
from app.models import Notification, Profile
from app.schemas.common import Page
from app.schemas.notification import NotificationRead
from app.services.notifications import generate_due_task_notifications
from app.utils.query import apply_sort, paginate

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _refresh_due_tasks(db: Session, user: Profile) -> None:
    """Lazily create 'task due' reminders - no background worker needed."""
    if generate_due_task_notifications(db, user):
        db.commit()


@router.get("", response_model=Page[NotificationRead])
def list_notifications(
    params: ListParams = Depends(list_params),
    unread_only: bool = False,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _refresh_due_tasks(db, user)
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = apply_sort(stmt, params, {"created_at": Notification.created_at}, default="created_at")
    return paginate(db, stmt, params)


@router.get("/unread-count")
def unread_count(user: Profile = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    _refresh_due_tasks(db, user)
    count = db.scalar(
        select(func.count()).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return {"count": count}


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_read(notification_id: uuid.UUID, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise not_found("Notification")
    notification.is_read = True
    db.commit()
    return notification


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
