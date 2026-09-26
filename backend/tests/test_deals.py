import pytest

from tests.conftest import auth_headers


@pytest.fixture
def stages(client, rep):
    pipelines = client.get("/api/pipelines", headers=auth_headers(rep)).json()
    return {stage["name"]: stage for stage in pipelines[0]["stages"]}


def create_deal(client, user, **fields):
    response = client.post("/api/deals", json={"name": "Big deal", "value": 1000, **fields}, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


def test_default_pipeline_is_created(client, rep, stages):
    assert list(stages) == ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
    assert stages["Won"]["stage_type"] == "won"


def test_new_deal_starts_in_first_stage(client, rep, stages):
    deal = create_deal(client, rep, currency="eur")
    assert deal["stage"]["name"] == "New"
    assert deal["status"] == "open"
    assert deal["probability"] == stages["New"]["probability"]
    assert deal["currency"] == "EUR"


def test_explicit_probability_and_stage(client, rep, stages):
    deal = create_deal(client, rep, stage_id=stages["Proposal"]["id"], probability=55)
    assert deal["stage"]["name"] == "Proposal" and deal["probability"] == 55


def test_move_deal_through_stages(client, rep, stages):
    deal = create_deal(client, rep)
    url = f"/api/deals/{deal['id']}/stage"
    headers = auth_headers(rep)

    moved = client.patch(url, json={"stage_id": stages["Negotiation"]["id"]}, headers=headers).json()
    assert moved["stage"]["name"] == "Negotiation" and moved["probability"] == 80 and moved["closed_at"] is None

    won = client.patch(url, json={"stage_id": stages["Won"]["id"]}, headers=headers).json()
    assert won["status"] == "won" and won["probability"] == 100 and won["closed_at"] is not None

    reopened = client.patch(url, json={"stage_id": stages["Qualified"]["id"]}, headers=headers).json()
    assert reopened["status"] == "open" and reopened["closed_at"] is None


def test_stage_from_other_pipeline_rejected(client, admin, rep):
    other = client.post(
        "/api/pipelines",
        json={"name": "Renewals", "stages": [{"name": "Open"}, {"name": "Done", "stage_type": "won", "probability": 100}]},
        headers=auth_headers(admin),
    ).json()
    deal = create_deal(client, rep)
    response = client.patch(
        f"/api/deals/{deal['id']}/stage", json={"stage_id": other["stages"][0]["id"]}, headers=auth_headers(rep)
    )
    assert response.status_code == 400


def test_rep_cannot_move_others_deal(client, rep, other_rep, stages):
    deal = create_deal(client, other_rep)
    response = client.patch(
        f"/api/deals/{deal['id']}/stage", json={"stage_id": stages["Won"]["id"]}, headers=auth_headers(rep)
    )
    assert response.status_code == 403


def test_board_groups_deals_by_stage(client, rep, stages):
    create_deal(client, rep, name="A", value=100)
    create_deal(client, rep, name="B", value=250)
    create_deal(client, rep, name="C", stage_id=stages["Won"]["id"])
    board = client.get("/api/deals/board", headers=auth_headers(rep)).json()
    columns = {column["stage"]["name"]: column for column in board["columns"]}
    assert columns["New"]["count"] == 2 and columns["New"]["total_value"] == 350
    assert [d["name"] for d in columns["Won"]["deals"]] == ["C"]


def test_deal_filters_and_company_stats(client, rep, stages):
    company = client.post("/api/companies", json={"name": "Initech"}, headers=auth_headers(rep)).json()
    create_deal(client, rep, name="Open one", value=500, company_id=company["id"])
    create_deal(client, rep, name="Won one", value=900, company_id=company["id"], stage_id=stages["Won"]["id"])
    headers = auth_headers(rep)

    items = client.get("/api/deals", params={"status": "won"}, headers=headers).json()["items"]
    assert [d["name"] for d in items] == ["Won one"]

    stats = client.get(f"/api/companies/{company['id']}", headers=headers).json()
    assert stats["deal_count"] == 2 and stats["open_deal_value"] == 500


def test_only_admin_edits_pipeline_stages(client, admin, manager, stages):
    url = f"/api/pipelines/stages/{stages['Proposal']['id']}"
    assert client.patch(url, json={"name": "Quote"}, headers=auth_headers(manager)).status_code == 403
    response = client.patch(url, json={"name": "Quote", "probability": 65}, headers=auth_headers(admin))
    assert response.status_code == 200 and response.json()["name"] == "Quote"


def test_invalid_deal_payloads(client, rep):
    headers = auth_headers(rep)
    assert client.post("/api/deals", json={"name": "X", "value": -5}, headers=headers).status_code == 422
    assert client.post("/api/deals", json={"name": "X", "currency": "DOLLARS"}, headers=headers).status_code == 422
    response = client.post(
        "/api/deals", json={"name": "X", "company_id": "00000000-0000-0000-0000-000000000000"}, headers=headers
    )
    assert response.status_code == 400
