"""Small helpers shared by the list endpoints: search, sort and paginate."""

import math
from typing import Any

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.dependencies.pagination import ListParams


def search_filter(term: str, *columns: Any) -> ColumnElement[bool]:
    """Case-insensitive 'contains' match across several columns."""
    pattern = f"%{term}%"
    return or_(*(column.ilike(pattern) for column in columns))


def apply_sort(stmt: Select, params: ListParams, allowed: dict[str, Any], default: str) -> Select:
    """Order by a whitelisted column (never trust a raw column name from the client)."""
    key = params.sort_by or default
    if key not in allowed:
        raise bad_request(f"Cannot sort by '{key}'. Allowed: {', '.join(sorted(allowed))}")
    column = allowed[key]
    ordered = column.asc() if params.sort_order == "asc" else column.desc()
    # Secondary sort on the primary key keeps paging stable when values tie.
    entity = stmt.column_descriptions[0]["entity"]
    return stmt.order_by(ordered.nulls_last(), entity.id)


def paginate(db: Session, stmt: Select, params: ListParams) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)).unique().all()
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": math.ceil(total / params.page_size) if total else 0,
    }


def get_or_404(db: Session, model: type, record_id: Any, name: str | None = None):
    record = db.get(model, record_id)
    if record is None:
        raise not_found(name or model.__name__)
    return record
