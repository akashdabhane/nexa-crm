from datetime import date, timedelta

import pytest

from tests.conftest import auth_headers


@pytest.fixture
def data(client, rep, other_rep):
    """Two reps with a small, known set of leads and deals."""
    headers, other = auth_headers(rep), auth_headers(other_rep)
    stages = {s["name"]: s["id"] for s in client.get("/api/pipelines", headers=headers).json()[0]["stages"]}

    for name, source in [("A", "website"), ("B", "website"), ("C", "referral"), ("D", "referral")]:
        client.post("/api/leads", json={"name": name, "source": source, "score": 50}, headers=headers)
    lead_id = client.get("/api/leads", params={"search": "C"}, headers=headers).json()["items"][0]["id"]
    client.post(f"/api/leads/{lead_id}/convert", json={"create_deal": False}, headers=headers)

    def deal(headers, name, value, stage):
        return client.post("/api/deals", json={"name": name, "value": value, "stage_id": stages[stage]}, headers=headers)

    deal(headers, "Won 1", 1000, "Won")
    deal(headers, "Won 2", 3000, "Won")
    deal(headers, "Lost 1", 500, "Lost")
    deal(headers, "Open 1", 2000, "Proposal")
    deal(other, "Other open", 4000, "Proposal")
    return stages


def test_lead_conversion_report(client, rep, data):
    report = client.get("/api/reports/lead-conversion", headers=auth_headers(rep)).json()
    assert report["total_leads"] == 4
    assert report["converted"] == 1
    assert report["conversion_rate"] == 25.0


def test_lead_sources_report(client, rep, data):
    report = {row["source"]: row for row in client.get("/api/reports/lead-sources", headers=auth_headers(rep)).json()}
    assert report["referral"]["leads"] == 2 and report["referral"]["conversion_rate"] == 50.0
    assert report["website"]["converted"] == 0


def test_win_loss_and_revenue(client, rep, data):
    headers = auth_headers(rep)
    win_loss = client.get("/api/reports/win-loss", headers=headers).json()
    assert (win_loss["won"], win_loss["lost"], win_loss["won_value"]) == (2, 1, 4000)
    assert win_loss["win_rate"] == 66.7

    revenue = client.get("/api/reports/revenue", headers=headers).json()
    assert revenue == [{"month": date.today().strftime("%Y-%m"), "deals": 2, "revenue": 4000.0}]


def test_date_filter_excludes_other_periods(client, rep, data):
    last_year = (date.today() - timedelta(days=365)).isoformat()
    params = {"start_date": last_year, "end_date": last_year}
    assert client.get("/api/reports/win-loss", params=params, headers=auth_headers(rep)).json()["won"] == 0
    bad = {"start_date": "2026-02-01", "end_date": "2026-01-01"}
    assert client.get("/api/reports/win-loss", params=bad, headers=auth_headers(rep)).status_code == 400


def test_pipeline_report(client, rep, data):
    rows = {row["stage"]: row for row in client.get("/api/reports/pipeline", headers=auth_headers(rep)).json()}
    assert "Won" not in rows
    assert rows["Proposal"]["count"] == 2 and rows["Proposal"]["value"] == 6000
    assert rows["Proposal"]["weighted_value"] == 3600  # 60% probability


def test_rep_performance_is_manager_only(client, rep, manager, data):
    assert client.get("/api/reports/rep-performance", headers=auth_headers(rep)).status_code == 403
    rows = client.get("/api/reports/rep-performance", headers=auth_headers(manager)).json()
    top = rows[0]
    assert top["name"] == "Riley Rep" and top["deals_won"] == 2 and top["revenue"] == 4000 and top["win_rate"] == 66.7


def test_dashboard_summary(client, rep, data):
    summary = client.get("/api/dashboard/summary", headers=auth_headers(rep)).json()
    totals = summary["totals"]
    assert totals["active_deals"] == 2 and totals["won_deals"] == 2 and totals["lost_deals"] == 1
    assert totals["pipeline_value"] == 6000 and totals["won_value"] == 4000
    assert totals["leads"] == 4 and totals["open_leads"] == 3
    assert totals["contacts"] == 1 and totals["companies"] == 0
    assert len(summary["pipeline"]) == 5
