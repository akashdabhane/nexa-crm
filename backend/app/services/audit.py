"""Audit logging. Entries are added to the caller's session, so they commit
(or roll back) together with the change they describe."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, Profile


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (uuid.UUID, date, datetime)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def apply_changes(record: Any, data: dict) -> dict:
    """Set attributes on `record` and return {field: [old, new]} for those that changed."""
    changes = {}
    for field, new in data.items():
        old = getattr(record, field)
        if _jsonable(old) != _jsonable(new):
            changes[field] = [_jsonable(old), _jsonable(new)]
            setattr(record, field, new)
    return changes


def record(
    db: Session,
    user: Profile | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    **details: Any,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details={key: _jsonable(value) for key, value in details.items()},
        )
    )
