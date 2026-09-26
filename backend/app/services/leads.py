"""Lead conversion: Lead -> Contact + Company (+ Deal), in one transaction."""

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict
from app.models import Activity, Company, Contact, Lead, Note, Profile
from app.models.enums import ContactStatus, LeadStatus
from app.schemas.lead import LeadConvert
from app.services import deals


def split_name(full_name: str) -> tuple[str, str | None]:
    first, _, last = full_name.strip().partition(" ")
    return first, (last.strip() or None)


def _find_or_create_company(db: Session, user: Profile, lead: Lead, options: LeadConvert) -> Company | None:
    if options.company_id is not None:
        company = db.get(Company, options.company_id)
        if company is None:
            raise bad_request("Company does not exist")
        return company
    if not lead.company_name:
        return None
    existing = db.scalar(
        select(Company).where(func.lower(Company.name) == lead.company_name.strip().lower()).limit(1)
    )
    if existing:
        return existing
    company = Company(name=lead.company_name.strip(), owner_id=lead.owner_id, created_by_id=user.id)
    db.add(company)
    db.flush()
    return company


def convert_lead(db: Session, user: Profile, lead: Lead, options: LeadConvert) -> dict:
    if lead.status == LeadStatus.CONVERTED:
        raise conflict("Lead has already been converted")

    company = _find_or_create_company(db, user, lead, options)

    first_name, last_name = split_name(lead.name)
    contact = Contact(
        first_name=first_name,
        last_name=last_name,
        email=lead.email,
        phone=lead.phone,
        status=ContactStatus.ACTIVE,
        company_id=company.id if company else None,
        owner_id=lead.owner_id,
        created_by_id=user.id,
    )
    db.add(contact)
    db.flush()

    deal = None
    if options.create_deal:
        deal = deals.create_deal(
            db,
            user=user,
            owner_id=lead.owner_id or user.id,
            name=options.deal_name or f"{lead.company_name or lead.name} deal",
            value=options.deal_value,
            expected_close_date=options.expected_close_date,
            company_id=company.id if company else None,
            contact_id=contact.id,
        )

    # Carry the lead's history over to the new contact (and company).
    for model in (Activity, Note):
        db.execute(
            update(model)
            .where(model.lead_id == lead.id)
            .values(
                contact_id=contact.id,
                company_id=func.coalesce(model.company_id, company.id if company else None),
            )
        )

    lead.status = LeadStatus.CONVERTED
    lead.converted_at = datetime.now(UTC)
    lead.converted_contact_id = contact.id
    lead.converted_company_id = company.id if company else None
    lead.converted_deal_id = deal.id if deal else None
    db.flush()

    return {"lead": lead, "contact": contact, "company": company, "deal": deal}
