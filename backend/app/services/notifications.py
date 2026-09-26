"""In-app notifications, created synchronously alongside the action that
triggers them. No queue or worker: "task due" reminders are generated lazily
when a user fetches their notifications."""

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Deal, Notification, Profile, Task
from app.models.enums import DealStatus, NotificationType, TaskStatus, UserRole


def notify(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    type: NotificationType,
    title: str,
    message: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    actor: Profile | None = None,
) -> None:
    """Queue a notification in the session. Nobody is notified about their own actions."""
    if user_id is None or (actor is not None and user_id == actor.id):
        return
    db.add(
        Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )


def notify_assignment(db: Session, actor: Profile, record, kind: str, type: NotificationType) -> None:
    """E.g. 'Max assigned you a lead: Grace Hopper'."""
    name = getattr(record, "name", None) or getattr(record, "title", "")
    notify(
        db,
        user_id=record.owner_id,
        type=type,
        title=f"New {kind} assigned to you",
        message=f"{actor.full_name} assigned you the {kind} “{name}”.",
        entity_type=kind,
        entity_id=record.id,
        actor=actor,
    )


def notify_deal_closed(db: Session, actor: Profile, deal: Deal) -> None:
    """Won/lost deals notify the owner and all managers/admins (except the actor)."""
    won = deal.status == DealStatus.WON
    managers = db.scalars(
        select(Profile.id).where(Profile.role.in_([UserRole.ADMIN, UserRole.MANAGER]), Profile.is_active.is_(True))
    ).all()
    for user_id in {deal.owner_id, *managers}:
        notify(
            db,
            user_id=user_id,
            type=NotificationType.DEAL_WON if won else NotificationType.DEAL_LOST,
            title=f"Deal {'won 🎉' if won else 'lost'}: {deal.name}",
            message=f"{actor.full_name} marked “{deal.name}” ({deal.currency} {deal.value:,.0f}) as {'won' if won else 'lost'}.",
            entity_type="deal",
            entity_id=deal.id,
            actor=actor,
        )


def generate_due_task_notifications(db: Session, user: Profile) -> int:
    """Create one 'task due' notification per open task due today/tomorrow or overdue."""
    tasks = db.scalars(
        select(Task).where(
            Task.owner_id == user.id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            Task.due_date <= date.today() + timedelta(days=1),
            Task.due_notified.is_(False),
        )
    ).unique().all()
    for task in tasks:
        overdue = task.due_date < date.today()
        when = "is overdue" if overdue else ("is due today" if task.due_date == date.today() else "is due tomorrow")
        db.add(
            Notification(
                user_id=user.id,
                type=NotificationType.TASK_DUE,
                title=f"Task {when}: {task.title}",
                message=f"Due {task.due_date:%b %d, %Y}.",
                entity_type="task",
                entity_id=task.id,
            )
        )
        task.due_notified = True
    return len(tasks)
