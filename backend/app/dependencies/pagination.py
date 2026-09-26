from dataclasses import dataclass
from typing import Literal

from fastapi import Query


@dataclass
class ListParams:
    page: int
    page_size: int
    search: str | None
    sort_by: str | None
    sort_order: Literal["asc", "desc"]


def list_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    sort_by: str | None = Query(None),
    sort_order: Literal["asc", "desc"] = Query("desc"),
) -> ListParams:
    """Common query parameters for every list endpoint."""
    return ListParams(
        page=page,
        page_size=page_size,
        search=search.strip() if search and search.strip() else None,
        sort_by=sort_by,
        sort_order=sort_order,
    )
