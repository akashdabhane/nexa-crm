from datetime import date, timedelta

import pytest

from tests.conftest import auth_headers


@pytest.fixture
def contact(client, rep):
    company = client.post("/api/companies", json={"name": "Hooli"}, headers=auth_headers(rep)).json()
    return client.post(
        "/api/contacts", json={"first_name": "Gavin", "company_id": company["id"]}, headers=auth_headers(rep)
    ).json()


def log(client, user, **fields):
    response = client.post("/api/activities", json={"type": "call", "subject": "Intro call", **fields}, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


# --- Activities & notes -------------------------------------------------------


def test_activity_requires_a_link(client, rep):
    response = client.post("/api/activities", json={"type": "call", "subject": "Orphan"}, headers=auth_headers(rep))
    assert response.status_code == 422


def test_activity_with_unknown_link_rejected(client, rep):
    response = client.post(
        "/api/activities",
        json={"type": "call", "subject": "X", "contact_id": "00000000-0000-0000-0000-000000000000"},
        headers=auth_headers(rep),
    )
    assert response.status_code == 400


def test_log_and_filter_activities(client, rep, contact):
    log(client, rep, contact_id=contact["id"], duration_minutes=15)
    log(client, rep, type="meeting", subject="Demo", contact_id=contact["id"])
    headers = auth_headers(rep)

    items = client.get("/api/activities", params={"contact_id": contact["id"]}, headers=headers).json()["items"]
    assert len(items) == 2 and items[0]["contact"]["name"] == "Gavin"

    items = client.get("/api/activities", params={"type": "meeting"}, headers=headers).json()["items"]
    assert [a["subject"] for a in items] == ["Demo"]


def test_only_author_or_manager_edits_activity(client, rep, other_rep, manager, contact):
    activity = log(client, rep, contact_id=contact["id"])
    url = f"/api/activities/{activity['id']}"
    assert client.patch(url, json={"subject": "Hacked"}, headers=auth_headers(other_rep)).status_code == 403
    assert client.patch(url, json={"subject": "Edited"}, headers=auth_headers(manager)).status_code == 200
    assert client.delete(url, headers=auth_headers(rep)).status_code == 204


def test_timeline_merges_activities_and_notes_newest_first(client, rep, contact):
    headers = auth_headers(rep)
    log(client, rep, contact_id=contact["id"], occurred_at="2026-01-01T10:00:00Z", subject="Old call")
    client.post("/api/notes", json={"body": "Prefers email", "contact_id": contact["id"]}, headers=headers)
    log(client, rep, contact_id=contact["id"], occurred_at="2020-01-01T10:00:00Z", subject="Ancient call")

    timeline = client.get("/api/timeline", params={"contact_id": contact["id"]}, headers=headers).json()
    assert [item["kind"] for item in timeline] == ["note", "activity", "activity"]
    assert timeline[1]["activity"]["subject"] == "Old call"

    # A company's timeline includes its contacts' entries.
    company_timeline = client.get(
        "/api/timeline", params={"company_id": contact["company"]["id"]}, headers=headers
    ).json()
    assert len(company_timeline) == 3


def test_timeline_needs_exactly_one_record(client, rep):
    assert client.get("/api/timeline", headers=auth_headers(rep)).status_code == 400


def test_lead_history_moves_to_contact_on_conversion(client, rep):
    headers = auth_headers(rep)
    lead = client.post("/api/leads", json={"name": "Ada Lovelace"}, headers=headers).json()
    log(client, rep, lead_id=lead["id"])
    client.post("/api/notes", json={"body": "Very promising", "lead_id": lead["id"]}, headers=headers)

    result = client.post(f"/api/leads/{lead['id']}/convert", json={"create_deal": False}, headers=headers).json()
    timeline = client.get("/api/timeline", params={"contact_id": result["contact_id"]}, headers=headers).json()
    assert len(timeline) == 2


# --- Tasks ---------------------------------------------------------------------


def create_task(client, user, **fields):
    response = client.post("/api/tasks", json={"title": "Follow up", **fields}, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


def test_task_defaults_and_completion(client, rep, contact):
    task = create_task(client, rep, contact_id=contact["id"])
    assert task["status"] == "pending" and task["priority"] == "medium" and task["owner"]["id"] == str(rep.id)

    done = client.patch(f"/api/tasks/{task['id']}", json={"status": "completed"}, headers=auth_headers(rep)).json()
    assert done["completed_at"] is not None
    reopened = client.patch(f"/api/tasks/{task['id']}", json={"status": "in_progress"}, headers=auth_headers(rep)).json()
    assert reopened["completed_at"] is None


def test_overdue_tasks(client, rep):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    late = create_task(client, rep, title="Late", due_date=yesterday)
    create_task(client, rep, title="Soon", due_date=tomorrow)
    create_task(client, rep, title="Late but done", due_date=yesterday, status="completed")

    assert late["is_overdue"] is True
    items = client.get("/api/tasks", params={"overdue": True}, headers=auth_headers(rep)).json()["items"]
    assert [t["title"] for t in items] == ["Late"]


def test_task_priority_sort(client, rep):
    for priority in ("low", "urgent", "medium"):
        create_task(client, rep, title=priority, priority=priority)
    items = client.get(
        "/api/tasks", params={"sort_by": "priority", "sort_order": "desc"}, headers=auth_headers(rep)
    ).json()["items"]
    assert [t["title"] for t in items] == ["urgent", "medium", "low"]


def test_manager_assigns_task_rep_cannot(client, manager, rep, other_rep):
    task = create_task(client, manager, owner_id=str(rep.id))
    assert task["owner"]["id"] == str(rep.id)
    response = client.post("/api/tasks", json={"title": "X", "owner_id": str(other_rep.id)}, headers=auth_headers(rep))
    assert response.status_code == 403
