"""LangChain tools the assistant's model can call.

Each tool runs the same endpoint function the UI's REST call runs, so validation, permissions, audit entries and
notifications are identical, and every save is committed immediately.

The DB session and current user arrive through the LangGraph run config (`configurable`), which LangChain injects
into the `config` parameter and hides from the model. Tools return `(content, artifact)`: the content is JSON for
the model, the artifact is the `SavedRecord` the chat UI links to.
"""

import json
import uuid
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import HTTPException
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes import activities, companies, contacts, leads, notes, tasks
from app.models import Company, Contact, Lead, Profile
from app.models.enums import ActivityType, LeadSource, TaskPriority
from app.schemas.activity import ActivityCreate
from app.schemas.assistant import SavedRecord
from app.schemas.company import CompanyCreate
from app.schemas.contact import ContactCreate
from app.schemas.lead import LeadCreate, LeadUpdate
from app.schemas.note import NoteCreate
from app.schemas.task import TaskCreate
from app.utils.query import search_filter

ToolResult = tuple[str, SavedRecord | None]

# Lead statuses the model may set ("converted" only happens through the convert action).
OpenLeadStatus = Literal["new", "contacted", "qualified", "unqualified"]
Score = Annotated[int | None, Field(ge=0, le=100, description="How promising the lead is, 0-100")]
LeadId = Annotated[str | None, "ID of the lead this belongs to"]
ContactId = Annotated[str | None, "ID of the contact this belongs to"]
CompanyId = Annotated[str | None, "ID of the company this belongs to"]


def _given(**fields) -> dict:
    """Drop the arguments the model left empty, so schema defaults apply."""
    return {key: value for key, value in fields.items() if value not in (None, "")}


def _error_text(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'input'}: {e['msg']}" for e in exc.errors())
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    return str(exc)


def _run(config: RunnableConfig, action: Callable[[Session, Profile], tuple[dict, SavedRecord | None]]) -> ToolResult:
    """Run a tool body with the request's DB session and user. Errors go back to the model as data."""
    db: Session = config["configurable"]["db"]
    user: Profile = config["configurable"]["user"]
    try:
        result, record = action(db, user)
    except (ValueError, HTTPException) as exc:  # ValidationError is a ValueError
        db.rollback()
        return json.dumps({"error": _error_text(exc)}), None
    return json.dumps(result, default=str), record


def _saved(type: str, action: str, record, label: str, link: tuple[str, uuid.UUID | None] | None = None) -> SavedRecord:
    link_type, link_id = link or (type, record.id)
    return SavedRecord(type=type, action=action, id=record.id, label=label, link_type=link_type, link_id=link_id)


def _parent_link(record) -> tuple[str, uuid.UUID | None]:
    """Activities and notes open on the page of the record they were logged on."""
    for kind in ("lead", "contact", "company"):
        if record_id := getattr(record, f"{kind}_id"):
            return kind, record_id
    return "activity", None


@tool(response_format="content_and_artifact")
def search_records(
    query: Annotated[str, "A name, email, phone or company to look for"], config: RunnableConfig
) -> ToolResult:
    """Find existing leads, contacts and companies by name, email or phone. Use before creating."""

    def action(db: Session, _user: Profile):
        term = query.strip()
        contact_name = func.concat_ws(" ", Contact.first_name, Contact.last_name)
        lead_match = search_filter(term, Lead.name, Lead.email, Lead.phone, Lead.company_name)
        found_leads = db.scalars(select(Lead).where(lead_match).limit(5)).unique()
        contact_match = search_filter(term, contact_name, Contact.email, Contact.phone)
        found_contacts = db.scalars(select(Contact).where(contact_match).limit(5)).unique()
        found_companies = db.scalars(select(Company).where(search_filter(term, Company.name)).limit(5)).unique()
        return {
            "leads": [
                {"id": l.id, "name": l.name, "email": l.email, "company": l.company_name, "status": l.status}
                for l in found_leads
            ],
            "contacts": [
                {"id": c.id, "name": c.full_name, "email": c.email, "company": c.company.name if c.company else None}
                for c in found_contacts
            ],
            "companies": [{"id": c.id, "name": c.name} for c in found_companies],
        }, None

    return _run(config, action)


@tool(response_format="content_and_artifact")
def create_lead(
    name: Annotated[str, "Person's full name"],
    config: RunnableConfig,
    email: Annotated[str | None, "Email address, only if the user gave it"] = None,
    phone: Annotated[str | None, "Phone number, only if the user gave it"] = None,
    company_name: Annotated[str | None, "Company the person works for"] = None,
    source: Annotated[LeadSource | None, "How the lead came in"] = None,
    status: Annotated[OpenLeadStatus | None, "Where the lead stands"] = None,
    score: Score = None,
) -> ToolResult:
    """Create a new lead: a prospect who isn't a customer yet."""

    def action(db: Session, user: Profile):
        fields = _given(
            name=name, email=email, phone=phone, company_name=company_name, source=source, status=status, score=score
        )
        lead = leads.create_lead(LeadCreate(**fields), user, db)
        return {"lead_id": lead.id}, _saved("lead", "created", lead, lead.name)

    return _run(config, action)


@tool(response_format="content_and_artifact")
def update_lead(
    lead_id: Annotated[str, "ID of the lead"],
    config: RunnableConfig,
    name: Annotated[str | None, "Person's full name"] = None,
    email: Annotated[str | None, "Email address"] = None,
    phone: Annotated[str | None, "Phone number"] = None,
    company_name: Annotated[str | None, "Company the person works for"] = None,
    source: Annotated[LeadSource | None, "How the lead came in"] = None,
    status: Annotated[OpenLeadStatus | None, "Where the lead stands"] = None,
    score: Score = None,
) -> ToolResult:
    """Change an existing lead, e.g. its status, score or details. Only send fields that change."""

    def action(db: Session, user: Profile):
        changes = _given(
            name=name, email=email, phone=phone, company_name=company_name, source=source, status=status, score=score
        )
        lead = leads.update_lead(uuid.UUID(lead_id), LeadUpdate(**changes), user, db)
        result = {"lead_id": lead.id, "status": lead.status, "score": lead.score}
        return result, _saved("lead", "updated", lead, lead.name)

    return _run(config, action)


@tool(response_format="content_and_artifact")
def create_company(
    name: Annotated[str, "Company name"],
    config: RunnableConfig,
    industry: Annotated[str | None, "Industry"] = None,
    website: Annotated[str | None, "Website URL"] = None,
    city: Annotated[str | None, "City"] = None,
    country: Annotated[str | None, "Country"] = None,
) -> ToolResult:
    """Create a company (an account)."""

    def action(db: Session, user: Profile):
        payload = CompanyCreate(**_given(name=name, industry=industry, website=website, city=city, country=country))
        company = companies.create_company(payload, user, db)
        return {"company_id": company.id}, _saved("company", "created", company, company.name)

    return _run(config, action)


@tool(response_format="content_and_artifact")
def create_contact(
    first_name: Annotated[str, "First name"],
    config: RunnableConfig,
    last_name: Annotated[str | None, "Last name"] = None,
    email: Annotated[str | None, "Email address, only if the user gave it"] = None,
    phone: Annotated[str | None, "Phone number, only if the user gave it"] = None,
    job_title: Annotated[str | None, "Job title"] = None,
    company_id: Annotated[str | None, "ID of the company they work for"] = None,
    city: Annotated[str | None, "City"] = None,
    country: Annotated[str | None, "Country"] = None,
) -> ToolResult:
    """Create a contact: a person you have an established relationship with."""

    def action(db: Session, user: Profile):
        payload = ContactCreate(
            **_given(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                job_title=job_title,
                company_id=company_id,
                city=city,
                country=country,
            )
        )
        contact = contacts.create_contact(payload, user, db)
        return {"contact_id": contact.id}, _saved("contact", "created", contact, contact.full_name)

    return _run(config, action)


@tool(response_format="content_and_artifact")
def log_activity(
    type: Annotated[ActivityType, "Kind of interaction"],
    subject: Annotated[str, "Short summary, e.g. 'Cold call about pricing'"],
    config: RunnableConfig,
    description: Annotated[str | None, "What was discussed"] = None,
    occurred_at: Annotated[str | None, "When it happened (ISO 8601). Omit if it just happened."] = None,
    duration_minutes: Annotated[int | None, Field(ge=0, description="How long it took, in minutes")] = None,
    lead_id: LeadId = None,
    contact_id: ContactId = None,
    company_id: CompanyId = None,
) -> ToolResult:
    """Log a call, email or meeting. Link it to at least one lead, contact or company."""

    def action(db: Session, user: Profile):
        payload = ActivityCreate(
            **_given(
                type=type,
                subject=subject,
                description=description,
                occurred_at=occurred_at,
                duration_minutes=duration_minutes,
                lead_id=lead_id,
                contact_id=contact_id,
                company_id=company_id,
            )
        )
        activity = activities.create_activity(payload, user, db)
        label = f"{activity.type.capitalize()}: {activity.subject}"
        return {"activity_id": activity.id}, _saved("activity", "created", activity, label, _parent_link(activity))

    return _run(config, action)


@tool(response_format="content_and_artifact")
def add_note(
    body: Annotated[str, "The note text"],
    config: RunnableConfig,
    lead_id: LeadId = None,
    contact_id: ContactId = None,
    company_id: CompanyId = None,
) -> ToolResult:
    """Save background information (needs, budget, preferences) on a lead, contact or company."""

    def action(db: Session, user: Profile):
        payload = NoteCreate(**_given(body=body, lead_id=lead_id, contact_id=contact_id, company_id=company_id))
        note = notes.create_note(payload, user, db)
        label = note.body if len(note.body) <= 60 else note.body[:57] + "…"
        return {"note_id": note.id}, _saved("note", "created", note, label, _parent_link(note))

    return _run(config, action)


@tool(response_format="content_and_artifact")
def create_task(
    title: Annotated[str, "What needs to be done"],
    config: RunnableConfig,
    description: Annotated[str | None, "More detail"] = None,
    due_date: Annotated[str | None, "Due date, YYYY-MM-DD"] = None,
    priority: Annotated[TaskPriority | None, "How urgent"] = None,
    contact_id: Annotated[str | None, "ID of the related contact"] = None,
    company_id: Annotated[str | None, "ID of the related company"] = None,
) -> ToolResult:
    """Create a follow-up task. Tasks can't link to leads: mention the lead's name in the title."""

    def action(db: Session, user: Profile):
        payload = TaskCreate(
            **_given(
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
                contact_id=contact_id,
                company_id=company_id,
            )
        )
        task = tasks.create_task(payload, user, db)
        return {"task_id": task.id}, _saved("task", "created", task, task.title)

    return _run(config, action)


TOOLS = [search_records, create_lead, update_lead, create_company, create_contact, log_activity, add_note, create_task]
