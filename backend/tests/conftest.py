"""Test setup.

- Uses a separate Postgres database: TEST_DATABASE_URL, or DATABASE_URL with
  the database name swapped for `nexa_crm_test`.
- Each test runs inside a transaction that is rolled back afterwards, so tests
  are isolated even though the app code calls `db.commit()`.
- Tokens are signed locally with an HS256 test secret, so the real
  `get_current_user` dependency is exercised without calling Supabase.
- The user fixtures are members of one organization (`org`); `auth_headers`
  sends it as X-Organization-Id. Records added directly through `db` land in
  that organization too.
"""

import os
import time
import uuid

os.environ["SUPABASE_JWT_SECRET"] = "test-secret-for-pytest-only-0123456789"

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.db.tenancy import set_current_org  # noqa: E402
from app.models import Base, Membership, Organization, Profile  # noqa: E402
from app.models.enums import UserRole  # noqa: E402

settings.supabase_jwt_secret = os.environ["SUPABASE_JWT_SECRET"]
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", settings.database_url.rsplit("/", 1)[0] + "/nexa_crm_test"
)
engine = create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def create_schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_token(user_id: uuid.UUID, email: str = "user@example.com", **overrides) -> str:
    claims = {
        "sub": str(user_id),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
        "user_metadata": {"full_name": "Test User"},
    }
    claims.update(overrides)
    return jwt.encode(claims, settings.supabase_jwt_secret, algorithm="HS256")


def auth_headers(user: Profile, org: Organization | uuid.UUID | None = None) -> dict:
    """Bearer token for `user`, working in `org` (default: the organization the fixture made them a member of)."""
    headers = {"Authorization": f"Bearer {make_token(user.id, user.email)}"}
    org_id = getattr(org, "id", org) or getattr(user, "test_org_id", None)
    if org_id is not None:
        headers["X-Organization-Id"] = str(org_id)
    return headers


def make_org(db: Session, name: str = "Acme Inc") -> Organization:
    organization = Organization(name=name)
    db.add(organization)
    db.commit()
    return organization


def make_member(db: Session, organization: Organization, role: UserRole, name: str) -> Profile:
    user = Profile(
        id=uuid.uuid4(),
        email=f"{name.lower().replace(' ', '.')}.{uuid.uuid4().hex[:6]}@example.com",
        full_name=name,
    )
    db.add(user)
    db.flush()
    db.add(Membership(organization_id=organization.id, user_id=user.id, role=role))
    db.commit()
    user.test_org_id = organization.id
    return user


@pytest.fixture
def org(db) -> Organization:
    organization = make_org(db)
    set_current_org(db, organization.id)
    return organization


@pytest.fixture
def admin(db, org) -> Profile:
    return make_member(db, org, UserRole.ADMIN, "Ada Admin")


@pytest.fixture
def manager(db, org) -> Profile:
    return make_member(db, org, UserRole.MANAGER, "Max Manager")


@pytest.fixture
def rep(db, org) -> Profile:
    return make_member(db, org, UserRole.SALES_REP, "Riley Rep")


@pytest.fixture
def other_rep(db, org) -> Profile:
    return make_member(db, org, UserRole.SALES_REP, "Sam Rep")
