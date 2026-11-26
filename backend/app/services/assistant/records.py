"""Filtered lists of CRM records for the assistant: what `list_records` shows and what an export of it contains.

Everyone can read every record in their organization (the session's tenancy filter scopes each query), so
listing needs no permission check. Team members are named the way the user says them ("created by Riya"),
and matched against the organization's members.
"""

import uuid
from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from app.db.tenancy import current_org
from app.models import Company, Contact, Deal, Lead, Membership, Profile, Task
from app.models.enums import ContactStatus, DealStatus, LeadSource, LeadStatus, TaskStatus
from app.schemas.assistant import ExportedFile, ExportFormat, ExportOffer, RecordFilters
from app.services.assistant.exports import Document, Section, Table, render
from app.utils.query import search_filter

PREVIEW_ROWS = 15  # rows list_records hands the model; enough to name a few, small enough for a local model
EXPORT_LIMIT = 5000

MODELS = {"lead": Lead, "contact": Contact, "company": Company, "deal": Deal, "task": Task}
PLURALS = {"lead": "leads", "contact": "contacts", "company": "companies", "deal": "deals", "task": "tasks"}
STATUSES: dict[str, type[StrEnum]] = {
    "lead": LeadStatus,
    "contact": ContactStatus,
    "deal": DealStatus,
    "task": TaskStatus,
}
ME = {"me", "myself", "i", "mine"}

Names = dict[uuid.UUID, str]
Column = tuple[str, Callable[[Any, Names], Any]]


def _label(value: str | None) -> str | None:
    """An enum value as people read it: "cold_call" → "Cold call"."""
    return value.replace("_", " ").capitalize() if value else value


def _created(record, _names: Names):
    return record.created_at.date()


def _owner(record, names: Names):
    return names.get(record.owner_id)


def _creator(record, names: Names):
    return names.get(record.created_by_id)


# The columns of each export, most important first (a slide shows only the first few).
COLUMNS: dict[str, list[Column]] = {
    "lead": [
        ("Name", lambda r, _: r.name),
        ("Company", lambda r, _: r.company_name),
        ("Email", lambda r, _: r.email),
        ("Phone", lambda r, _: r.phone),
        ("Status", lambda r, _: _label(r.status)),
        ("Source", lambda r, _: _label(r.source)),
        ("Score", lambda r, _: r.score),
        ("Owner", _owner),
        ("Created by", _creator),
        ("Created", _created),
    ],
    "contact": [
        ("Name", lambda r, _: r.full_name),
        ("Company", lambda r, _: r.company.name if r.company else None),
        ("Email", lambda r, _: r.email),
        ("Phone", lambda r, _: r.phone),
        ("Job title", lambda r, _: r.job_title),
        ("Status", lambda r, _: _label(r.status)),
        ("City", lambda r, _: r.city),
        ("Country", lambda r, _: r.country),
        ("Tags", lambda r, _: r.tags),
        ("Owner", _owner),
        ("Created by", _creator),
        ("Created", _created),
    ],
    "company": [
        ("Name", lambda r, _: r.name),
        ("Industry", lambda r, _: r.industry),
        ("Email", lambda r, _: r.email),
        ("Phone", lambda r, _: r.phone),
        ("Website", lambda r, _: r.website),
        ("City", lambda r, _: r.city),
        ("Country", lambda r, _: r.country),
        ("Employees", lambda r, _: r.employee_count),
        ("Owner", _owner),
        ("Created by", _creator),
        ("Created", _created),
    ],
    "deal": [
        ("Name", lambda r, _: r.name),
        ("Company", lambda r, _: r.company.name if r.company else None),
        ("Value", lambda r, _: r.value),
        ("Currency", lambda r, _: r.currency),
        ("Stage", lambda r, _: r.stage.name),
        ("Status", lambda r, _: _label(r.status)),
        ("Probability %", lambda r, _: r.probability),
        ("Expected close", lambda r, _: r.expected_close_date),
        ("Contact", lambda r, _: r.contact.full_name if r.contact else None),
        ("Owner", _owner),
        ("Created by", _creator),
        ("Created", _created),
    ],
    "task": [
        ("Title", lambda r, _: r.title),
        ("Due date", lambda r, _: r.due_date),
        ("Priority", lambda r, _: _label(r.priority)),
        ("Status", lambda r, _: _label(r.status)),
        ("Owner", _owner),
        ("Created by", _creator),
        ("Created", _created),
    ],
}


def _search_columns(record_type: str) -> list:
    if record_type == "lead":
        return [Lead.name, Lead.email, Lead.phone, Lead.company_name]
    if record_type == "contact":
        return [func.concat_ws(" ", Contact.first_name, Contact.last_name), Contact.email, Contact.phone, Contact.city]
    if record_type == "company":
        return [Company.name, Company.industry, Company.email, Company.website, Company.city]
    if record_type == "deal":
        return [Deal.name]
    return [Task.title]


def member_names(db: Session) -> Names:
    """Everyone in the current organization, by profile id."""
    rows = db.execute(
        select(Profile.id, Profile.full_name)
        .join(Membership, Membership.user_id == Profile.id)
        .where(Membership.organization_id == current_org(db))
    ).all()
    return {row.id: row.full_name for row in rows}


def _find_member(db: Session, user: Profile, term: str, names: Names) -> uuid.UUID:
    """The one team member a name or email means. Errors (as data for the model) list who there is."""
    term = term.strip()
    if term.lower() in ME:
        return user.id
    emails = dict(
        db.execute(
            select(Profile.id, Profile.email).where(Profile.id.in_(names.keys()))
        ).all()
    )
    words = term.lower().split()
    found = [
        member
        for member, name in names.items()
        if all(word in f"{name} {emails.get(member, '')}".lower() for word in words)
    ]
    exact = [member for member in found if names[member].lower() == term.lower()]
    if len(exact) == 1 or len(found) == 1:
        return (exact or found)[0]
    team = ", ".join(sorted(names.values()))
    if not found:
        raise ValueError(f"No team member matches '{term}'. The team: {team}.")
    raise ValueError(f"'{term}' matches several team members: {', '.join(sorted(names[m] for m in found))}.")


def _enum_value(value: str, allowed: type[StrEnum], what: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    if normalized not in {item.value for item in allowed}:
        raise ValueError(f"Unknown {what} '{value}'. Use one of: {', '.join(item.value for item in allowed)}.")
    return normalized


def _query(db: Session, user: Profile, filters: RecordFilters, names: Names):
    """The SELECT for the filters, and a description of them ("created by Riya Sharma, status qualified")."""
    kind = filters.record_type
    model = MODELS[kind]
    conditions: list[ColumnElement[bool]] = []
    described: list[str] = []
    if filters.search:
        words = filters.search.split()
        conditions.append(and_(*(search_filter(word, *_search_columns(kind)) for word in words)))
        described.append(f"matching “{filters.search}”")
    if filters.created_by:
        member = _find_member(db, user, filters.created_by, names)
        conditions.append(model.created_by_id == member)
        described.append(f"created by {names.get(member, 'you')}")
    if filters.owner:
        member = _find_member(db, user, filters.owner, names)
        conditions.append(model.owner_id == member)
        described.append(f"owned by {names.get(member, 'you')}")
    if filters.status:
        if kind not in STATUSES:
            raise ValueError(f"{PLURALS[kind].capitalize()} have no status.")
        status = _enum_value(filters.status, STATUSES[kind], "status")
        conditions.append(model.status == status)
        described.append(f"status {_label(status).lower()}")
    if filters.source:
        if kind != "lead":
            raise ValueError("Only leads have a source.")
        source = _enum_value(filters.source, LeadSource, "source")
        conditions.append(Lead.source == source)
        described.append(f"from {_label(source).lower()}")
    if filters.location:
        if kind not in ("company", "contact"):
            raise ValueError("Only companies and contacts have a location.")
        places = (model.city, model.country, model.address)
        conditions.append(and_(*(search_filter(word, *places) for word in filters.location.split())))
        described.append(f"in {filters.location.strip()}")
    if filters.created_from:
        conditions.append(model.created_at >= filters.created_from)
    if filters.created_to:
        conditions.append(model.created_at < filters.created_to + timedelta(days=1))
    if filters.created_from or filters.created_to:
        start, end = filters.created_from or "the start", filters.created_to or "today"
        described.append(f"created {start} to {end}")
    stmt = select(model).where(*conditions).order_by(model.created_at.desc(), model.id)
    return stmt, ", ".join(described)


def _table(filters: RecordFilters, records: list, names: Names, total: int) -> Table:
    columns = COLUMNS[filters.record_type]
    return Table(
        columns=[header for header, _ in columns],
        rows=[[value(record, names) for _, value in columns] for record in records],
        total=total,
    )


def _count(db: Session, stmt) -> int:
    return db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0


def describe(filters: RecordFilters, total: int, description: str) -> str:
    noun = filters.record_type if total == 1 else PLURALS[filters.record_type]
    return f"{total} {noun}" + (f" {description}" if description else "")


def list_records(db: Session, user: Profile, filters: RecordFilters) -> tuple[dict, ExportOffer | None]:
    """How many records match, the first rows for the model, and the export offer the chat shows for them."""
    names = member_names(db)
    stmt, description = _query(db, user, filters, names)
    total = _count(db, stmt)
    records = db.scalars(stmt.limit(PREVIEW_ROWS)).unique().all()
    table = _table(filters, records, names, total)
    rows = [
        {"id": str(record.id), **{h: v for h, v in zip(table.columns, row) if v not in (None, "", [])}}
        for record, row in zip(records, table.rows)
    ]
    label = describe(filters, total, description)
    result = {"found": label, "total": total, "showing": len(rows), "rows": rows}
    offer = ExportOffer(**filters.model_dump(), total=total, label=label) if total else None
    return result, offer


def export_records(db: Session, user: Profile, filters: RecordFilters, format: ExportFormat) -> ExportedFile:
    """The full list (up to EXPORT_LIMIT rows) as a file."""
    names = member_names(db)
    stmt, description = _query(db, user, filters, names)
    total = _count(db, stmt)
    records = db.scalars(stmt.limit(EXPORT_LIMIT)).unique().all()
    title = PLURALS[filters.record_type].capitalize() + (f" {description}" if description else "")
    document = Document(
        title=title,
        subtitle=f"{describe(filters, total, '')} · exported by {user.full_name}",
        sections=[Section(heading=PLURALS[filters.record_type].capitalize(), table=_table(filters, records, names, total))],
    )
    return render(document, format)
