"""Load realistic demo data so the app looks populated.

    python -m scripts.seed           # only if the CRM tables are empty
    python -m scripts.seed --reset   # wipe CRM data (keeps real user profiles) and reseed

Demo users are placeholder profiles (they can't log in); they own records so
dashboards and reports have a team to show. Your real Supabase account becomes
Admin on first login because no demo user is an admin. If you log in first and
then run `--reset`, some records are assigned to you as well.
"""

import argparse
import random
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select

from app.db.session import SessionLocal
from app.models import (
    Activity,
    AuditLog,
    Company,
    Contact,
    Deal,
    Lead,
    Note,
    Notification,
    Pipeline,
    Profile,
    Task,
)
from app.models.enums import (
    ActivityType,
    ContactStatus,
    LeadSource,
    LeadStatus,
    StageType,
    TaskPriority,
    TaskStatus,
    UserRole,
)
from app.services.deals import apply_stage
from app.services.pipelines import get_default_pipeline

random.seed(42)
NOW = datetime.now(UTC)
TODAY = date.today()
DEMO_DOMAIN = "nexacrm.demo"

DEMO_USERS = [
    ("Priya Sharma", UserRole.MANAGER),
    ("Daniel Kim", UserRole.SALES_REP),
    ("Sofia Martinez", UserRole.SALES_REP),
    ("Marcus Johnson", UserRole.SALES_REP),
    ("Emily Chen", UserRole.SALES_REP),
]

COMPANIES = [
    ("Northwind Traders", "Retail", "Seattle", "USA", 420),
    ("Contoso Pharmaceuticals", "Healthcare", "Boston", "USA", 2300),
    ("Globex Logistics", "Logistics", "Chicago", "USA", 860),
    ("Initech Software", "Software", "Austin", "USA", 150),
    ("Umbrella Health", "Healthcare", "London", "UK", 5400),
    ("Stark Manufacturing", "Manufacturing", "Detroit", "USA", 3100),
    ("Wayne Financial", "Financial Services", "New York", "USA", 1200),
    ("Acme Robotics", "Manufacturing", "San Jose", "USA", 310),
    ("Blue Harbor Hotels", "Hospitality", "Miami", "USA", 980),
    ("Evergreen Energy", "Energy", "Denver", "USA", 640),
    ("Pinnacle Analytics", "Software", "Toronto", "Canada", 85),
    ("Sunrise Foods", "Food & Beverage", "Sacramento", "USA", 530),
    ("Vertex Telecom", "Telecommunications", "Dallas", "USA", 4200),
    ("Horizon Education", "Education", "Bangalore", "India", 260),
    ("Summit Legal Group", "Legal", "Washington", "USA", 120),
    ("Atlas Construction", "Construction", "Phoenix", "USA", 740),
    ("Nimbus Cloud", "Software", "Berlin", "Germany", 190),
    ("Crescent Media", "Media", "Los Angeles", "USA", 340),
    ("Orchid Retail Group", "Retail", "Singapore", "Singapore", 1500),
    ("Keystone Insurance", "Financial Services", "Hartford", "USA", 2100),
    ("Lumen Biotech", "Healthcare", "San Diego", "USA", 410),
    ("Redwood Capital", "Financial Services", "San Francisco", "USA", 75),
]

FIRST_NAMES = [
    "Olivia", "Liam", "Ava", "Noah", "Isabella", "Ethan", "Mia", "Lucas", "Amelia", "Mason", "Harper",
    "Logan", "Aria", "James", "Chloe", "Benjamin", "Zoe", "Arjun", "Ananya", "Hiro", "Yuki", "Fatima",
    "Omar", "Elena", "Mateo", "Grace", "Leo", "Nora", "Samuel", "Layla", "David", "Priyanka",
]
LAST_NAMES = [
    "Anderson", "Bennett", "Carter", "Diaz", "Evans", "Foster", "Garcia", "Hughes", "Iyer", "Jensen",
    "Khan", "Lopez", "Mehta", "Nguyen", "Owens", "Patel", "Quinn", "Reyes", "Singh", "Tanaka", "Walker",
    "Young", "Zimmerman", "Brooks", "Murphy", "Rossi", "Schmidt", "Novak",
]
TITLES = [
    "CEO", "CTO", "VP of Sales", "Head of Operations", "Procurement Manager", "IT Director",
    "Marketing Director", "Finance Manager", "Product Manager", "Operations Analyst", "COO",
]
TAGS = ["decision-maker", "champion", "technical", "budget-holder", "vip", "newsletter", "partner"]
DEAL_PRODUCTS = [
    "Annual license", "Enterprise plan", "Implementation", "Support renewal", "Platform upgrade",
    "Pilot project", "Data migration", "Training package", "Multi-year agreement", "Expansion seats",
]
CALL_SUBJECTS = ["Discovery call", "Follow-up call", "Pricing discussion", "Check-in call", "Contract questions"]
MEETING_SUBJECTS = ["Product demo", "Onsite workshop", "Quarterly business review", "Kickoff meeting", "Negotiation meeting"]
EMAIL_SUBJECTS = ["Sent proposal", "Shared case study", "Sent pricing sheet", "Intro email", "Contract sent for review"]
NOTE_BODIES = [
    "Budget approved for Q{q}. Decision expected within 3 weeks.",
    "Main competitor in the deal is using aggressive discounting.",
    "Prefers email over calls. Best reached in the morning.",
    "Legal review needed before signing — loop in their counsel early.",
    "Very interested in the analytics module; asked for a technical deep-dive.",
    "Current vendor contract ends next quarter — good timing.",
    "Asked for references from similar companies in their industry.",
]
TASK_TITLES = [
    "Send proposal", "Follow up on pricing", "Schedule demo", "Prepare contract", "Call to check in",
    "Share case study", "Book QBR meeting", "Confirm budget with finance", "Send onboarding plan",
]


def days_ago(days: float) -> datetime:
    return NOW - timedelta(days=days, hours=random.randint(0, 9), minutes=random.randint(0, 59))


def ensure_demo_users(db) -> list[Profile]:
    users = []
    for name, role in DEMO_USERS:
        email = f"{name.lower().replace(' ', '.')}@{DEMO_DOMAIN}"
        user = db.scalar(select(Profile).where(Profile.email == email))
        if user is None:
            user = Profile(id=uuid.uuid5(uuid.NAMESPACE_DNS, email), email=email, full_name=name, role=role)
            db.add(user)
        users.append(user)
    db.flush()
    return users


def reset(db) -> None:
    for model in (Notification, AuditLog, Note, Activity, Task, Lead, Deal, Contact, Company):
        db.execute(delete(model))
    db.execute(delete(Pipeline))


def seed(db) -> None:
    users = ensure_demo_users(db)
    # Real accounts that already signed in also get records, so "My tasks" etc. aren't empty.
    real_users = db.scalars(
        select(Profile).where(Profile.email.not_like(f"%@{DEMO_DOMAIN}"), Profile.is_active.is_(True))
    ).all()
    reps = users[1:] + list(real_users)
    pipeline = get_default_pipeline(db)
    stages = {stage.name: stage for stage in pipeline.stages}

    # Companies & contacts -----------------------------------------------------
    companies = []
    for name, industry, city, country, employees in COMPANIES:
        slug = name.lower().split()[0]
        company = Company(
            name=name,
            industry=industry,
            city=city,
            country=country,
            employee_count=employees,
            website=f"{slug}.example.com",
            email=f"info@{slug}.example.com",
            phone=f"+1 555 {random.randint(100, 999)} {random.randint(1000, 9999)}",
            address=f"{random.randint(10, 999)} {random.choice(['Market', 'Oak', 'Pine', 'Main', 'Harbor'])} Street",
            owner_id=random.choice(reps).id,
            created_at=days_ago(random.randint(120, 300)),
        )
        companies.append(company)
    db.add_all(companies)
    db.flush()

    contacts = []
    used_names = set()
    for company in companies:
        for _ in range(random.randint(2, 4)):
            first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            while (first, last) in used_names:
                first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            used_names.add((first, last))
            domain = company.website
            contacts.append(
                Contact(
                    first_name=first,
                    last_name=last,
                    email=f"{first.lower()}.{last.lower()}@{domain}",
                    phone=f"+1 555 {random.randint(100, 999)} {random.randint(1000, 9999)}",
                    job_title=random.choice(TITLES),
                    city=company.city,
                    country=company.country,
                    status=random.choices(list(ContactStatus), weights=[6, 3, 1])[0],
                    tags=random.sample(TAGS, k=random.randint(0, 2)),
                    company_id=company.id,
                    owner_id=company.owner_id,
                    created_at=company.created_at + timedelta(days=random.randint(1, 60)),
                )
            )
    db.add_all(contacts)
    db.flush()

    # Deals: a spread across stages, with closed deals over the last 8 months ---
    stage_weights = {
        "New": 5, "Contacted": 5, "Qualified": 5, "Proposal": 5, "Negotiation": 4, "Won": 12, "Lost": 6,
    }
    deals = []
    for stage_name, count in stage_weights.items():
        for _ in range(count):
            company = random.choice(companies)
            company_contacts = [c for c in contacts if c.company_id == company.id]
            created = days_ago(random.randint(10, 240))
            deal = Deal(
                name=f"{company.name.split()[0]} — {random.choice(DEAL_PRODUCTS)}",
                value=Decimal(random.choice([5, 8, 12, 15, 20, 25, 30, 45, 60, 80, 120]) * 1000),
                currency="USD",
                company_id=company.id,
                contact_id=random.choice(company_contacts).id,
                owner_id=company.owner_id if random.random() < 0.7 else random.choice(reps).id,
                description="Opportunity identified during account review.",
                created_at=created,
            )
            apply_stage(deal, stages[stage_name])
            if stage_name in ("Won", "Lost"):
                deal.closed_at = min(created + timedelta(days=random.randint(14, 90)), NOW - timedelta(days=1))
                deal.expected_close_date = deal.closed_at.date()
            else:
                deal.expected_close_date = TODAY + timedelta(days=random.randint(-10, 75))
            deals.append(deal)
    db.add_all(deals)
    db.flush()

    # Leads -----------------------------------------------------------------------
    lead_statuses = (
        [LeadStatus.NEW] * 8 + [LeadStatus.CONTACTED] * 7 + [LeadStatus.QUALIFIED] * 6 + [LeadStatus.UNQUALIFIED] * 4
    )
    sources = list(LeadSource)
    source_weights = [9, 6, 3, 5, 4, 3, 1]
    leads = []
    lead_companies = ["Brightline Studios", "Quantum Freight", "Maple & Co", "Ironclad Security", "Novaform Labs",
                      "Silverline Travel", "Cobalt Systems", "Fernwood Clinics", "Bluepeak Outdoors", "Arcadia Games",
                      "Helix Genomics", "Tidewater Marine", "Solstice Solar", "Granite Partners", "Parkside Dental"]
    for status in lead_statuses:
        first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        company_name = random.choice(lead_companies)
        leads.append(
            Lead(
                name=f"{first} {last}",
                email=f"{first.lower()}@{company_name.lower().split()[0]}.example.com",
                phone=f"+1 555 {random.randint(100, 999)} {random.randint(1000, 9999)}",
                company_name=company_name,
                source=random.choices(sources, weights=source_weights)[0],
                status=status,
                score={LeadStatus.NEW: 20, LeadStatus.CONTACTED: 40, LeadStatus.QUALIFIED: 70, LeadStatus.UNQUALIFIED: 10}[status]
                + random.randint(0, 25),
                owner_id=random.choice(reps).id,
                created_at=days_ago(random.randint(1, 120)),
            )
        )
    # Converted leads, linked to the contacts/companies/deals they became.
    for deal in random.sample(deals, 10):
        contact = next(c for c in contacts if c.id == deal.contact_id)
        company = next(c for c in companies if c.id == deal.company_id)
        converted_at = deal.created_at
        leads.append(
            Lead(
                name=contact.full_name,
                email=contact.email,
                phone=contact.phone,
                company_name=company.name,
                source=random.choices(sources, weights=source_weights)[0],
                status=LeadStatus.CONVERTED,
                score=random.randint(70, 95),
                owner_id=deal.owner_id,
                created_at=converted_at - timedelta(days=random.randint(5, 30)),
                converted_at=converted_at,
                converted_contact_id=contact.id,
                converted_company_id=company.id,
                converted_deal_id=deal.id,
            )
        )
    db.add_all(leads)
    db.flush()

    # Activities & notes ---------------------------------------------------------------
    activities = []
    for deal in deals:
        for _ in range(random.randint(1, 4)):
            kind = random.choice(list(ActivityType))
            subject = random.choice(
                {ActivityType.CALL: CALL_SUBJECTS, ActivityType.MEETING: MEETING_SUBJECTS, ActivityType.EMAIL: EMAIL_SUBJECTS}[kind]
            )
            start = deal.created_at
            end = deal.closed_at or NOW
            occurred = start + (end - start) * random.random()
            activities.append(
                Activity(
                    type=kind,
                    subject=subject,
                    description=random.choice(
                        ["Positive conversation, next step agreed.", "Walked through requirements.", "Discussed timeline and budget.", None]
                    ),
                    occurred_at=occurred,
                    duration_minutes=random.choice([15, 30, 45, 60]) if kind != ActivityType.EMAIL else None,
                    deal_id=deal.id,
                    contact_id=deal.contact_id,
                    company_id=deal.company_id,
                    owner_id=deal.owner_id,
                    created_at=occurred,
                )
            )
    for lead in leads[:20]:
        if lead.status in (LeadStatus.CONTACTED, LeadStatus.QUALIFIED):
            activities.append(
                Activity(
                    type=ActivityType.CALL,
                    subject="Qualification call",
                    description="Asked about team size, budget and timeline.",
                    occurred_at=lead.created_at + timedelta(days=2),
                    duration_minutes=20,
                    lead_id=lead.id,
                    owner_id=lead.owner_id,
                    created_at=lead.created_at + timedelta(days=2),
                )
            )
    db.add_all(activities)

    notes = []
    for deal in random.sample(deals, 18):
        created = deal.created_at + timedelta(days=random.randint(1, 10))
        notes.append(
            Note(
                body=random.choice(NOTE_BODIES).format(q=random.randint(1, 4)),
                deal_id=deal.id,
                contact_id=deal.contact_id,
                company_id=deal.company_id,
                owner_id=deal.owner_id,
                created_at=created,
                updated_at=created,
            )
        )
    for contact in random.sample(contacts, 10):
        notes.append(Note(body=random.choice(NOTE_BODIES).format(q=2), contact_id=contact.id, company_id=contact.company_id, owner_id=contact.owner_id))
    db.add_all(notes)

    # Tasks: overdue, due soon, later and completed -----------------------------------
    open_deals = [d for d in deals if d.status == StageType.OPEN]
    tasks = []
    for index in range(36):
        deal = random.choice(open_deals)
        offset = random.choice([-6, -3, -1, 0, 0, 1, 2, 3, 5, 7, 10, 14, 21])
        status = TaskStatus.COMPLETED if index % 4 == 0 else random.choice([TaskStatus.PENDING, TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        tasks.append(
            Task(
                title=random.choice(TASK_TITLES),
                description=None,
                due_date=TODAY + timedelta(days=offset),
                priority=random.choices(list(TaskPriority), weights=[2, 5, 3, 1])[0],
                status=status,
                completed_at=NOW - timedelta(days=random.randint(0, 5)) if status == TaskStatus.COMPLETED else None,
                owner_id=deal.owner_id,
                created_by_id=deal.owner_id,
                deal_id=deal.id,
                contact_id=deal.contact_id,
                company_id=deal.company_id,
            )
        )
    db.add_all(tasks)
    db.flush()

    print(
        f"Seeded {len(users)} demo users, {len(companies)} companies, {len(contacts)} contacts, "
        f"{len(leads)} leads, {len(deals)} deals, {len(activities)} activities, {len(notes)} notes, {len(tasks)} tasks."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete existing CRM data before seeding")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            reset(db)
        elif db.scalar(select(func.count()).select_from(Company)):
            print("Database already has data. Run with --reset to wipe CRM data and reseed.")
            return
        seed(db)
        db.commit()


if __name__ == "__main__":
    main()
