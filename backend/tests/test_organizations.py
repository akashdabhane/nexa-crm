"""Multi-tenancy: organizations, memberships, invitations, and data isolation."""

import uuid

import pytest
from sqlalchemy import func, select, update

from app.db.tenancy import NoOrganizationError, set_current_org
from app.models import Company, Contact, Deal, Lead, LeadIntegration, Membership, Notification, Pipeline
from app.models.enums import IntegrationKind, MembershipStatus, UserRole
from tests.conftest import auth_headers, make_member, make_org, make_token
from tests.test_reports import data  # noqa: F401  (fixture: leads and won/lost/open deals in `org`)


@pytest.fixture
def other_org(db):
    return make_org(db, "Globex")


@pytest.fixture
def outsider(db, other_org):
    """Admin of a different organization."""
    return make_member(db, other_org, UserRole.ADMIN, "Olive Outsider")


@pytest.fixture
def acme_company(client, rep):
    response = client.post("/api/companies", json={"name": "Acme Secret Co"}, headers=auth_headers(rep))
    assert response.status_code == 201, response.text
    return response.json()


# --- Signing up gives no access ----------------------------------------------


def test_new_user_belongs_to_no_organization(client, acme_company):
    headers = {"Authorization": f"Bearer {make_token(uuid.uuid4(), 'newbie@example.com')}"}

    me = client.get("/api/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] is None
    assert client.get("/api/organizations", headers=headers).json() == []

    no_org = client.get("/api/companies", headers=headers)
    assert no_org.status_code == 400
    assert no_org.headers["X-Organization-Error"] == "1"


def test_cannot_enter_an_organization_you_are_not_in(client, org, outsider, acme_company):
    headers = auth_headers(outsider, org)  # a real organization id, but not theirs
    response = client.get("/api/companies", headers=headers)
    assert response.status_code == 404
    assert response.headers["X-Organization-Error"] == "1"
    assert client.get(f"/api/companies/{acme_company['id']}", headers=headers).status_code == 404

    garbage = auth_headers(outsider, uuid.uuid4())
    assert client.get("/api/companies", headers=garbage).status_code == 404


# --- Isolation ----------------------------------------------------------------


def test_organizations_never_see_each_others_records(client, rep, outsider, acme_company):
    theirs = auth_headers(outsider)
    company_id = acme_company["id"]

    assert client.get("/api/companies", headers=theirs).json()["total"] == 0
    assert client.get(f"/api/companies/{company_id}", headers=theirs).status_code == 404
    assert client.patch(f"/api/companies/{company_id}", json={"name": "Pwned"}, headers=theirs).status_code == 404
    assert client.delete(f"/api/companies/{company_id}", headers=theirs).status_code == 404
    assert client.get("/api/companies/industries", headers=theirs).json() == []

    # Can't link their own records to ours either.
    contact = client.post(
        "/api/contacts", json={"first_name": "Eve", "company_id": company_id}, headers=theirs
    )
    assert contact.status_code == 400

    # Their own data works and stays theirs.
    assert client.post("/api/companies", json={"name": "Globex Co"}, headers=theirs).status_code == 201
    names = [c["name"] for c in client.get("/api/companies", headers=auth_headers(rep)).json()["items"]]
    assert names == ["Acme Secret Co"]


def test_dashboard_and_reports_count_only_own_organization(client, rep, outsider, acme_company):
    client.post("/api/contacts", json={"first_name": "Ann"}, headers=auth_headers(rep))
    client.post("/api/leads", json={"name": "Lead A"}, headers=auth_headers(rep))

    ours = client.get("/api/dashboard/summary", headers=auth_headers(rep)).json()["totals"]
    theirs = client.get("/api/dashboard/summary", headers=auth_headers(outsider)).json()["totals"]
    assert (ours["companies"], ours["contacts"], ours["leads"]) == (1, 1, 1)
    assert (theirs["companies"], theirs["contacts"], theirs["leads"]) == (0, 0, 0)


def test_user_list_and_assignment_are_per_organization(client, rep, manager, outsider):
    emails = {u["email"] for u in client.get("/api/users", headers=auth_headers(manager)).json()}
    assert rep.email in emails and outsider.email not in emails

    response = client.post(
        "/api/leads", json={"name": "Lead", "owner_id": str(outsider.id)}, headers=auth_headers(manager)
    )
    assert response.status_code == 400


def test_each_organization_has_its_own_pipeline(client, rep, outsider):
    ours = client.get("/api/pipelines", headers=auth_headers(rep)).json()
    theirs = client.get("/api/pipelines", headers=auth_headers(outsider)).json()
    assert len(ours) == len(theirs) == 1
    assert ours[0]["id"] != theirs[0]["id"]


def test_bulk_updates_stay_inside_the_organization(db, org, other_org, rep):
    rep_in_other = Membership(organization_id=other_org.id, user_id=rep.id, role=UserRole.SALES_REP)
    db.add(rep_in_other)
    for organization in (org, other_org):
        db.add(Notification(organization_id=organization.id, user_id=rep.id, type="task_due", title="Hi"))
    db.commit()

    set_current_org(db, org.id)
    db.execute(update(Notification).where(Notification.user_id == rep.id).values(is_read=True))
    db.commit()

    set_current_org(db, other_org.id)
    assert db.scalars(select(Notification.is_read)).all() == [False]


def test_a_new_organization_sees_no_numbers_from_another(client, rep, outsider, data):
    """Regression: aggregate-only queries (counts/sums of deals) once ignored the organization."""
    theirs = auth_headers(outsider)

    summary = client.get("/api/dashboard/summary", headers=theirs).json()
    totals = summary["totals"]
    assert all(value == 0 for value in totals.values()), totals
    assert all(stage["count"] == 0 and stage["value"] == 0 for stage in summary["pipeline"]), summary["pipeline"]
    assert summary["lead_sources"] == [] and summary["recent_activities"] == []

    reports = {
        name: client.get(f"/api/reports/{name}", headers=theirs).json()
        for name in ("lead-conversion", "pipeline", "revenue", "win-loss", "rep-performance", "lead-sources")
    }
    assert reports["lead-conversion"]["total_leads"] == 0, reports["lead-conversion"]
    assert reports["lead-conversion"]["avg_days_to_convert"] is None
    assert all(stage["count"] == 0 and stage["value"] == 0 for stage in reports["pipeline"])
    assert (reports["win-loss"]["won"], reports["win-loss"]["lost"]) == (0, 0)
    assert reports["revenue"] == []
    assert reports["lead-sources"] == []
    assert [row["user_id"] for row in reports["rep-performance"]] == [str(outsider.id)]
    assert reports["rep-performance"][0]["revenue"] == 0 and reports["rep-performance"][0]["open_deals"] == 0

    board = client.get("/api/deals/board", headers=theirs).json()
    assert all(col["count"] == 0 and col["total_value"] == 0 and col["deals"] == [] for col in board["columns"])
    for path in ("deals", "leads", "contacts", "companies", "activities", "tasks", "notes"):
        assert client.get(f"/api/{path}", headers=theirs).json()["total"] == 0, path

    # And the owning organization still sees its own numbers.
    ours = client.get("/api/dashboard/summary", headers=auth_headers(rep)).json()["totals"]
    assert ours["won_deals"] == 2 and ours["leads"] == 4


def test_aggregate_only_queries_are_scoped(db, org, other_org, rep):
    db.add(Lead(organization_id=other_org.id, name="Elsewhere", status="converted"))
    db.commit()
    set_current_org(db, org.id)
    # The table only appears inside functions here: no entity, no select_from().
    assert db.execute(select(func.count(), func.count().filter(Lead.status == "converted"))).one() == (0, 0)
    assert db.scalar(select(func.coalesce(func.sum(Deal.value), 0))) == 0
    set_current_org(db, other_org.id)
    assert db.execute(select(func.count(), func.count().filter(Lead.status == "converted"))).one() == (1, 1)


def test_scoping_fails_closed_without_an_organization(db, org, rep):
    db.add(Company(name="Visible only with an org"))
    db.commit()

    set_current_org(db, None)
    assert db.scalars(select(Company)).all() == []
    assert db.scalar(select(func.count()).select_from(Company)) == 0
    db.add(Contact(first_name="Orphan"))
    with pytest.raises(NoOrganizationError):
        db.flush()
    db.rollback()


def test_webhook_leads_go_to_the_integrations_organization(client, db, rep, outsider, other_org):
    integration = LeadIntegration(
        organization_id=other_org.id,
        name="Globex form",
        kind=IntegrationKind.WEBHOOK,
        platform="facebook",
        webhook_token="t" * 40,
        created_by_id=outsider.id,
    )
    db.add(integration)
    db.commit()

    response = client.post(f"/api/integrations/webhooks/{'t' * 40}", json={"name": "Wanda Webhook"})
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1

    assert client.get("/api/leads", headers=auth_headers(rep)).json()["total"] == 0
    theirs = client.get("/api/leads", headers=auth_headers(outsider)).json()
    assert [lead["name"] for lead in theirs["items"]] == ["Wanda Webhook"]
    assert theirs["items"][0]["owner"]["id"] == str(outsider.id)


# --- Organizations ------------------------------------------------------------


def test_create_organization_makes_you_admin(client, db, acme_company):
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {make_token(user_id, 'founder@example.com')}"}

    response = client.post("/api/organizations", json={"name": "Initech"}, headers=headers)
    assert response.status_code == 201, response.text
    created = response.json()
    assert (created["name"], created["role"], created["member_count"]) == ("Initech", "admin", 1)

    assert [o["name"] for o in client.get("/api/organizations", headers=headers).json()] == ["Initech"]
    headers["X-Organization-Id"] = created["id"]
    assert client.get("/api/me", headers=headers).json()["role"] == "admin"
    assert client.get("/api/companies", headers=headers).json()["total"] == 0
    set_current_org(db, uuid.UUID(created["id"]))
    assert db.scalar(select(Pipeline).where(Pipeline.is_default.is_(True))) is not None


def test_only_admins_rename_the_organization(client, admin, rep):
    assert client.patch("/api/organizations/current", json={"name": "X"}, headers=auth_headers(rep)).status_code == 403
    response = client.patch("/api/organizations/current", json={"name": "Acme Renamed"}, headers=auth_headers(admin))
    assert response.status_code == 200
    assert client.get("/api/organizations/current", headers=auth_headers(rep)).json()["name"] == "Acme Renamed"


# --- Invitations ----------------------------------------------------------------


def test_invite_accept_flow(client, db, org, admin, rep, acme_company):
    assert client.post("/api/invitations", json={"email": "x@example.com"}, headers=auth_headers(rep)).status_code == 403

    invite = client.post(
        "/api/invitations", json={"email": "New.Hire@Example.com", "role": "manager"}, headers=auth_headers(admin)
    )
    assert invite.status_code == 201, invite.text
    assert invite.json()["email"] == "new.hire@example.com"
    assert len(client.get("/api/invitations", headers=auth_headers(admin)).json()) == 1

    # Someone else can't see or take it.
    stranger = {"Authorization": f"Bearer {make_token(uuid.uuid4(), 'stranger@example.com')}"}
    assert client.get("/api/me/invitations", headers=stranger).json() == []
    assert client.post(f"/api/me/invitations/{invite.json()['id']}/accept", headers=stranger).status_code == 404

    # The invited person signs up, sees it, accepts it, and is in.
    new_hire = {"Authorization": f"Bearer {make_token(uuid.uuid4(), 'new.hire@example.com')}"}
    mine = client.get("/api/me/invitations", headers=new_hire).json()
    assert [(i["organization"]["name"], i["role"]) for i in mine] == [("Acme Inc", "manager")]
    accepted = client.post(f"/api/me/invitations/{mine[0]['id']}/accept", headers=new_hire)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["role"] == "manager"

    new_hire["X-Organization-Id"] = str(org.id)
    assert client.get("/api/companies", headers=new_hire).json()["total"] == 1
    assert client.get("/api/invitations", headers=auth_headers(admin)).json() == []
    # Accepted invitations can't be reused.
    assert client.post(f"/api/me/invitations/{mine[0]['id']}/accept", headers=new_hire).status_code == 404


def test_unconfirmed_email_cannot_accept(client, admin):
    client.post("/api/invitations", json={"email": "unconfirmed@example.com"}, headers=auth_headers(admin))
    token = make_token(uuid.uuid4(), "unconfirmed@example.com", user_metadata={"email_verified": False})
    assert client.get("/api/me/invitations", headers={"Authorization": f"Bearer {token}"}).json() == []


def test_cannot_invite_existing_member_and_can_revoke(client, admin, rep):
    assert client.post("/api/invitations", json={"email": rep.email}, headers=auth_headers(admin)).status_code == 400
    invite = client.post("/api/invitations", json={"email": "temp@example.com"}, headers=auth_headers(admin)).json()
    again = client.post("/api/invitations", json={"email": "temp@example.com"}, headers=auth_headers(admin)).json()
    assert again["id"] == invite["id"]  # refreshed, not duplicated
    assert client.delete(f"/api/invitations/{invite['id']}", headers=auth_headers(admin)).status_code == 204
    assert client.get("/api/invitations", headers=auth_headers(admin)).json() == []


# --- Managing members -----------------------------------------------------------


def test_disabling_and_removing_members(client, db, admin, rep):
    response = client.patch(f"/api/users/{rep.id}", json={"is_active": False}, headers=auth_headers(admin))
    assert response.status_code == 200 and response.json()["is_active"] is False
    blocked = client.get("/api/companies", headers=auth_headers(rep))
    assert blocked.status_code == 403 and blocked.headers["X-Organization-Error"] == "1"
    # Only this organization's access changed, not the account.
    assert client.get("/api/me", headers={"Authorization": auth_headers(rep)["Authorization"]}).status_code == 200

    client.patch(f"/api/users/{rep.id}", json={"is_active": True}, headers=auth_headers(admin))
    assert client.get("/api/companies", headers=auth_headers(rep)).status_code == 200

    assert client.delete(f"/api/users/{rep.id}", headers=auth_headers(admin)).status_code == 204
    assert client.get("/api/companies", headers=auth_headers(rep)).status_code == 404
    assert db.scalar(select(Membership).where(Membership.user_id == rep.id)) is None


def test_organization_keeps_an_admin(client, db, org, admin, manager):
    assert client.delete(f"/api/users/{admin.id}", headers=auth_headers(admin)).status_code == 400
    # A second admin can't strip the last other admin either... once only one is left.
    client.patch(f"/api/users/{manager.id}", json={"role": "admin"}, headers=auth_headers(admin))
    assert client.patch(f"/api/users/{admin.id}", json={"role": "sales_rep"}, headers=auth_headers(manager)).status_code == 200
    response = client.patch(f"/api/users/{manager.id}", json={"is_active": False}, headers=auth_headers(manager))
    assert response.status_code == 400  # can't deactivate yourself


def test_member_roles_are_per_organization(client, db, org, other_org, rep):
    db.add(Membership(organization_id=other_org.id, user_id=rep.id, role=UserRole.ADMIN, status=MembershipStatus.ACTIVE))
    db.commit()
    token = {"Authorization": auth_headers(rep)["Authorization"]}

    assert client.get("/api/me", headers={**token, "X-Organization-Id": str(org.id)}).json()["role"] == "sales_rep"
    assert client.get("/api/me", headers={**token, "X-Organization-Id": str(other_org.id)}).json()["role"] == "admin"
    orgs = client.get("/api/organizations", headers=token).json()
    assert sorted((o["name"], o["role"]) for o in orgs) == [("Acme Inc", "sales_rep"), ("Globex", "admin")]
