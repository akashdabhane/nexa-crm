import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import ListParams, list_params
from app.models import Profile, Task
from app.models.enums import NotificationType, TaskPriority, TaskStatus
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import notifications
from app.services.permissions import check_owner_change, ensure_can_edit, owner_for_create
from app.services.related import validate_related
from app.utils.query import apply_sort, get_or_404, paginate, search_filter

router = APIRouter(prefix="/tasks", tags=["tasks"])

OPEN_STATUSES = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
# Sort priorities by urgency rather than alphabetically.
PRIORITY_RANK = case(
    {TaskPriority.URGENT: 4, TaskPriority.HIGH: 3, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 1},
    value=Task.priority,
    else_=0,
)
SORTABLE = {
    "due_date": Task.due_date,
    "priority": PRIORITY_RANK,
    "status": Task.status,
    "title": Task.title,
    "created_at": Task.created_at,
}


def _sync_completed_at(task: Task) -> None:
    if task.status == TaskStatus.COMPLETED and task.completed_at is None:
        task.completed_at = datetime.now(UTC)
    elif task.status != TaskStatus.COMPLETED:
        task.completed_at = None


@router.get("", response_model=Page[TaskRead])
def list_tasks(
    params: ListParams = Depends(list_params),
    status_filter: TaskStatus | None = Query(None, alias="status"),
    priority: TaskPriority | None = None,
    owner_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    deal_id: uuid.UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    overdue: bool = False,
    open_only: bool = False,
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Task)
    if params.search:
        stmt = stmt.where(search_filter(params.search, Task.title, Task.description))
    for column, value in {
        Task.status: status_filter,
        Task.priority: priority,
        Task.owner_id: owner_id,
        Task.contact_id: contact_id,
        Task.company_id: company_id,
        Task.deal_id: deal_id,
    }.items():
        if value is not None:
            stmt = stmt.where(column == value)
    if due_from:
        stmt = stmt.where(Task.due_date >= due_from)
    if due_to:
        stmt = stmt.where(Task.due_date <= due_to)
    if overdue:
        stmt = stmt.where(Task.due_date < date.today(), Task.status.in_(OPEN_STATUSES))
    if open_only:
        stmt = stmt.where(Task.status.in_(OPEN_STATUSES))
    stmt = apply_sort(stmt, params, SORTABLE, default="due_date")
    return paginate(db, stmt, params)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"owner_id"})
    validate_related(db, data)
    task = Task(**data, owner_id=owner_for_create(db, user, payload.owner_id), created_by_id=user.id)
    _sync_completed_at(task)
    db.add(task)
    db.flush()
    notifications.notify_assignment(db, user, task, "task", NotificationType.TASK_ASSIGNED)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: uuid.UUID, _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_or_404(db, Task, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = get_or_404(db, Task, task_id)
    ensure_can_edit(user, task)
    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data:
        check_owner_change(db, user, task, data["owner_id"])
    validate_related(db, data)
    for field in ("title", "priority", "status"):
        if field in data and data[field] is None:
            data.pop(field)
    if "due_date" in data:
        task.due_notified = False  # a new due date deserves a new reminder
    reassigned = "owner_id" in data and data["owner_id"] != task.owner_id
    for field, value in data.items():
        setattr(task, field, value)
    _sync_completed_at(task)
    if reassigned:
        notifications.notify_assignment(db, user, task, "task", NotificationType.TASK_ASSIGNED)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: uuid.UUID, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    task = get_or_404(db, Task, task_id)
    ensure_can_edit(user, task)
    db.delete(task)
    db.commit()
