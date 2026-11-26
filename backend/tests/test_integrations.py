import hashlib
import hmac
import json

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import AuditLog, Lead, Note, Notification
from app.models.enums import UserRole
from app.services import lead_import, meta_leads
from tests.conftest import auth_headers, make_member, make_org

FACEBOOK_TSV = (
    "id\tcreated_time\tcampaign_name\tform_name\tfull_name\temail\tphone_number\twhat's_your_budget?\tplatform\n"
    "l:1001\t2026-11-01T10:00:00+0000\tSpring\tDemo form\tAda Lovelace\tada@example.com\tp:+15550001\t$5k\tig\n"
    "l:1002\t2026-11-01T11:00:00+0000\tSpring\tDemo form\tAlan Turing\tALAN@example.com\tp:+15550002\t$10k\tfb\n"
    "l:1003\t2026-11-01T12:00:00+0000\tSpring\tDemo form\tAlan Again\talan@example.com\t\t\tfb\n"
)


# --- Field mapping -----------------------------------------------------------


def test_parse_row_maps_loose_column_names():
    parsed = lead_import.parse_row(
        {"First Name": "Grace", "lastName": "Hopper", "E-mail": "grace@navy.mil", "Company": "Navy", "Twitter Handle": "@grace", "Budget": "$1k"},
        default_platform=None,
    )
    assert parsed.name == "Grace Hopper"
    assert (parsed.email, parsed.company_name, parsed.social_handle) == ("grace@navy.mil", "Navy", "@grace")
    assert parsed.extras == {"Budget": "$1k"}

    assert lead_import.parse_row({"email": "solo@example.com"}).name == "solo"
    with pytest.raises(ValueError):
        lead_import.parse_row({"budget": "$1k"})
    bad = lead_import.parse_row({"name": "X", "email": "not-an-email"})
    assert bad.email is None and bad.extras["Email (invalid)"] == "not-an-email"


# --- CSV import --------------------------------------------------------------


def test_csv_import_dry_run_then_import(client, db, rep):
    headers = auth_headers(rep)
    body = {"csv_text": FACEBOOK_TSV, "platform": "facebook", "score": 40}

    preview = client.post("/api/leads/import", json={**body, "dry_run": True}, headers=headers)
    assert preview.status_code == 200, preview.text
    data = preview.json()
    assert (data["created"], data["skipped"], data["failed"]) == (2, 1, 0)
    assert data["preview"][0]["phone"] == "+15550001" and data["preview"][0]["social_platform"] == "instagram"
    assert "full_name" in data["columns"]
    assert db.scalars(select(Lead)).all() == []

    response = client.post("/api/leads/import", json=body, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["created"], data["skipped"]) == (2, 1)
    assert data["issues"][0]["reason"] == "A lead with this email already exists"

    ada = db.scalar(select(Lead).where(Lead.name == "Ada Lovelace"))
    assert (ada.social_platform, ada.source, ada.external_id, ada.score) == ("instagram", "social_media", "1001", 40)
    assert ada.owner_id == rep.id
    note = db.scalar(select(Note).where(Note.lead_id == ada.id))
    assert "What's your budget?: $5k" in note.body and "Campaign name: Spring" in note.body
    assert db.scalar(select(AuditLog).where(AuditLog.entity_id == ada.id)).action == "lead.imported"

    again = client.post("/api/leads/import", json=body, headers=headers).json()
    assert (again["created"], again["skipped"]) == (0, 3)

    listed = client.get("/api/leads", params={"social_platform": "instagram"}, headers=headers).json()
    assert [lead["name"] for lead in listed["items"]] == ["Ada Lovelace"]


def test_csv_import_rules(client, rep, other_rep, manager, db):
    csv_text = "Name,Email\nZed,zed@example.com\n"
    assert client.post("/api/leads/import", json={"csv_text": csv_text, "owner_id": str(other_rep.id)}, headers=auth_headers(rep)).status_code == 403
    assert client.post("/api/leads/import", json={"csv_text": "Name,Email\n"}, headers=auth_headers(rep)).status_code == 400

    response = client.post("/api/leads/import", json={"csv_text": csv_text, "owner_id": str(other_rep.id)}, headers=auth_headers(manager))
    assert response.json()["created"] == 1
    lead = db.scalar(select(Lead).where(Lead.name == "Zed"))
    assert (lead.social_platform, lead.source) == (None, "other")
    note = db.scalar(select(Notification).where(Notification.user_id == other_rep.id))
    assert note.title == "1 imported lead assigned to you"


# --- Generic webhook integrations --------------------------------------------


def create_webhook_integration(client, admin, **fields):
    payload = {"name": "Zapier – Instagram", "kind": "webhook", "platform": "instagram", **fields}
    response = client.post("/api/integrations", json=payload, headers=auth_headers(admin))
    assert response.status_code == 201, response.text
    return response.json()


def test_only_admins_manage_integrations(client, manager):
    assert client.get("/api/integrations", headers=auth_headers(manager)).status_code == 403
    assert client.post("/api/integrations", json={"name": "X"}, headers=auth_headers(manager)).status_code == 403


def test_webhook_creates_leads_for_default_owner(client, db, admin, rep):
    integration = create_webhook_integration(client, admin, default_owner_id=str(rep.id), default_score=30)
    url = f"/api/integrations/webhooks/{integration['webhook_token']}"

    response = client.post(url, json={"leads": [
        {"full_name": "Linus T", "email": "linus@example.com", "username": "@linus", "id": "ig-1", "message": "Price?"},
        {"name": "No Contact"},
        {"foo": "bar"},
    ]})
    assert response.status_code == 200, response.text
    assert (response.json()["created"], response.json()["failed"]) == (2, 1)

    lead = db.scalar(select(Lead).where(Lead.email == "linus@example.com"))
    assert (lead.owner_id, lead.social_platform, lead.social_handle, lead.score) == (rep.id, "instagram", "@linus", 30)
    assert str(lead.integration_id) == integration["id"]
    notification = db.scalar(select(Notification).where(Notification.entity_id == lead.id))
    assert notification.user_id == rep.id and "Instagram" in notification.title
    audit = db.scalar(select(AuditLog).where(AuditLog.entity_id == lead.id))
    assert audit.user_id is None and audit.details["channel"] == "webhook"

    # Same platform lead id again (e.g. a retried delivery) is skipped; a single object body works too.
    again = client.post(url, json={"full_name": "Linus T", "email": "other@example.com", "id": "ig-1"}).json()
    assert (again["created"], again["skipped"]) == (0, 1)

    listed = client.get("/api/integrations", headers=auth_headers(admin)).json()
    assert listed[0]["leads_imported"] == 2 and listed[0]["last_lead_at"]


def test_webhook_token_pause_and_rotation(client, admin):
    integration = create_webhook_integration(client, admin)
    token = integration["webhook_token"]
    assert client.post("/api/integrations/webhooks/not-a-real-token-123456789", json={"name": "A"}).status_code == 404

    client.patch(f"/api/integrations/{integration['id']}", json={"is_active": False}, headers=auth_headers(admin))
    assert client.post(f"/api/integrations/webhooks/{token}", json={"name": "A"}).status_code == 403

    rotated = client.post(f"/api/integrations/{integration['id']}/rotate-token", headers=auth_headers(admin)).json()
    assert rotated["webhook_token"] != token
    assert client.post(f"/api/integrations/webhooks/{token}", json={"name": "A"}).status_code == 404


# --- Meta Lead Ads (Facebook + Instagram) ------------------------------------

META_LEAD = {
    "id": "9001",
    "platform": "ig",
    "form_name": "Insta form",
    "field_data": [
        {"name": "full_name", "values": ["Margaret Hamilton"]},
        {"name": "email", "values": ["margaret@example.com"]},
        {"name": "phone_number", "values": ["+15559999"]},
        {"name": "favorite_product", "values": ["Apollo"]},
    ],
}


@pytest.fixture
def meta(monkeypatch):
    monkeypatch.setattr(settings, "integrations_secret", "test-integrations-secret")
    monkeypatch.setattr(settings, "meta_app_secret", "test-app-secret")
    monkeypatch.setattr(settings, "meta_verify_token", "verify-me")
    calls = {"subscribed": [], "tokens": []}
    monkeypatch.setattr(meta_leads, "get_page", lambda page_id, token: {"id": page_id, "name": "Nexa Page"})
    monkeypatch.setattr(meta_leads, "subscribe_page", lambda page_id, token: calls["subscribed"].append(page_id))

    def get_lead(leadgen_id, token):
        calls["tokens"].append(token)
        return {**META_LEAD, "id": leadgen_id}

    monkeypatch.setattr(meta_leads, "get_lead", get_lead)
    return calls


def create_meta_integration(client, admin):
    response = client.post(
        "/api/integrations",
        json={"name": "Facebook Page", "kind": "meta_lead_ads", "meta_page_id": "12345", "access_token": "EAAG-page-token-xyz"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 201, response.text
    return response.json()


def signed(body: dict) -> tuple[bytes, dict]:
    raw = json.dumps(body).encode()
    signature = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()
    return raw, {"X-Hub-Signature-256": f"sha256={signature}", "Content-Type": "application/json"}


def test_meta_integration_connects_page(client, db, admin, meta):
    integration = create_meta_integration(client, admin)
    assert integration["meta_page_name"] == "Nexa Page" and integration["has_access_token"]
    assert integration["platform"] == "facebook" and "access_token" not in integration
    assert meta["subscribed"] == ["12345"]
    # The token is stored encrypted.
    from app.models import LeadIntegration

    row = db.get(LeadIntegration, integration["id"])
    assert "EAAG" not in row.access_token_encrypted


def test_meta_needs_token_storage_secret(client, admin, meta, monkeypatch):
    monkeypatch.setattr(settings, "integrations_secret", "")
    response = client.post(
        "/api/integrations",
        json={"name": "FB", "kind": "meta_lead_ads", "meta_page_id": "1", "access_token": "EAAG-page-token-xyz"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 503


def test_meta_webhook_verification(client, meta):
    params = {"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "1158201444"}
    response = client.get("/api/integrations/meta/webhook", params=params)
    assert response.status_code == 200 and response.text == "1158201444"
    assert client.get("/api/integrations/meta/webhook", params={**params, "hub.verify_token": "nope"}).status_code == 403


def test_meta_leadgen_event_imports_lead(client, db, admin, meta):
    create_meta_integration(client, admin)
    event = {"object": "page", "entry": [{"id": "12345", "changes": [{"field": "leadgen", "value": {"leadgen_id": "9001", "page_id": "12345"}}]}]}
    raw, headers = signed(event)

    assert client.post("/api/integrations/meta/webhook", content=raw, headers={**headers, "X-Hub-Signature-256": "sha256=bad"}).status_code == 403

    response = client.post("/api/integrations/meta/webhook", content=raw, headers=headers)
    assert response.status_code == 200 and response.json()["created"] == 1
    assert meta["tokens"] == ["EAAG-page-token-xyz"]
    lead = db.scalar(select(Lead).where(Lead.email == "margaret@example.com"))
    assert (lead.social_platform, lead.external_id, lead.owner_id) == ("instagram", "9001", admin.id)
    note = db.scalar(select(Note).where(Note.lead_id == lead.id))
    assert "Favorite product: Apollo" in note.body and "Form: Insta form" in note.body

    # Meta retries deliveries; the same lead isn't created twice.
    assert client.post("/api/integrations/meta/webhook", content=raw, headers=headers).json()["created"] == 0


def test_meta_sync_pulls_page_leads(client, db, admin, meta, monkeypatch):
    integration = create_meta_integration(client, admin)
    seen_since = []

    def iter_page_leads(page_id, token, since=None):
        seen_since.append(since)
        yield {**META_LEAD, "id": "7001"}
        yield {**META_LEAD, "id": "7002", "platform": "fb", "field_data": [{"name": "full_name", "values": ["Katherine Johnson"]}]}

    monkeypatch.setattr(meta_leads, "iter_page_leads", iter_page_leads)
    response = client.post(f"/api/integrations/{integration['id']}/sync", headers=auth_headers(admin))
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 2
    katherine = db.scalar(select(Lead).where(Lead.name == "Katherine Johnson"))
    assert katherine.social_platform == "facebook"

    client.post(f"/api/integrations/{integration['id']}/sync", headers=auth_headers(admin))
    assert seen_since[0] is None and seen_since[1] is not None


def test_meta_signature_check():
    settings_secret = settings.meta_app_secret
    try:
        settings.meta_app_secret = "s3cret"
        body = b'{"a":1}'
        good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
        assert meta_leads.verify_signature(body, good)
        assert not meta_leads.verify_signature(body + b" ", good)
        assert not meta_leads.verify_signature(body, None)
    finally:
        settings.meta_app_secret = settings_secret


def test_lead_to_row_flattens_field_data():
    row = meta_leads.lead_to_row({**META_LEAD, "campaign_name": "Fall"})
    assert row["full_name"] == ["Margaret Hamilton"] and row["leadgen_id"] == "9001"
    assert row["platform"] == "ig" and row["Campaign"] == "Fall" and row["Form"] == "Insta form"


def test_csv_import_ignores_non_numeric_scores(client, rep):
    # "inf" parses as a float, and used to crash the whole import with OverflowError.
    csv_text = "Name,Score\nAlice,inf\nBob,NaN\nCara,-Infinity\nDan,250\n"
    response = client.post("/api/leads/import", json={"csv_text": csv_text, "score": 30}, headers=auth_headers(rep))
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 4
    leads = {l["name"]: l["score"] for l in client.get("/api/leads", headers=auth_headers(rep)).json()["items"]}
    assert leads == {"Alice": 30, "Bob": 30, "Cara": 30, "Dan": 100}


def test_meta_webhook_keeps_each_organizations_rows_apart(client, db, admin, meta):
    # Two organizations connected the same Page: each gets its own lead, and that lead's note, audit entry and
    # notification stay in its organization (they used to be filed under the next organization in the loop).
    create_meta_integration(client, admin)
    beta = make_org(db, "Beta")
    beta_admin = make_member(db, beta, UserRole.ADMIN, "Bea Admin")
    create_meta_integration(client, beta_admin)

    raw, headers = signed(
        {"object": "page", "entry": [{"id": "12345", "changes": [{"field": "leadgen", "value": {"page_id": "12345", "leadgen_id": "L-777"}}]}]}
    )
    response = client.post("/api/integrations/meta/webhook", content=raw, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 2

    all_orgs = {"all_orgs": True}
    leads = db.scalars(select(Lead).where(Lead.external_id == "L-777").execution_options(**all_orgs)).all()
    assert {lead.organization_id for lead in leads} == {admin.test_org_id, beta.id}
    for lead in leads:
        note = db.scalar(select(Note).where(Note.lead_id == lead.id).execution_options(**all_orgs))
        audit = db.scalar(select(AuditLog).where(AuditLog.entity_id == lead.id).execution_options(**all_orgs))
        notification = db.scalar(select(Notification).where(Notification.entity_id == lead.id).execution_options(**all_orgs))
        assert note.organization_id == audit.organization_id == notification.organization_id == lead.organization_id


def test_meta_sync_limit_leaves_the_rest_for_the_next_sync(client, db, admin, meta, monkeypatch):
    integration = create_meta_integration(client, admin)
    monkeypatch.setattr(meta_leads, "MAX_SYNC_LEADS", 2)
    seen_since = []

    def iter_page_leads(page_id, token, since=None):
        seen_since.append(since)
        for n in range(3):
            yield {**META_LEAD, "id": f"80{n}", "field_data": [{"name": "full_name", "values": [f"Lead {n}"]}]}

    monkeypatch.setattr(meta_leads, "iter_page_leads", iter_page_leads)
    url = f"/api/integrations/{integration['id']}/sync"
    first = client.post(url, headers=auth_headers(admin)).json()
    assert first["created"] == 2 and first["has_more"] is True
    # The window didn't move, and the leads already imported don't use up the next sync's limit.
    second = client.post(url, headers=auth_headers(admin)).json()
    assert second["created"] == 1 and second["has_more"] is False
    assert seen_since[:2] == [None, None]
    client.post(url, headers=auth_headers(admin))
    assert seen_since[2] is not None
