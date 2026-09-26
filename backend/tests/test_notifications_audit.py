from datetime import date, timedelta

from tests.conftest import auth_headers


def notifications_for(client, user):
    return client.get("/api/notifications", headers=auth_headers(user)).json()["items"]


def stage_ids(client, user):
    return {s["name"]: s["id"] for s in client.get("/api/pipelines", headers=auth_headers(user)).json()[0]["stages"]}


def test_assigning_a_lead_notifies_the_new_owner(client, manager, rep):
    client.post("/api/leads", json={"name": "Hot lead", "owner_id": str(rep.id)}, headers=auth_headers(manager))
    items = notifications_for(client, rep)
    assert len(items) == 1
    assert items[0]["type"] == "lead_assigned" and "Hot lead" in items[0]["message"]
    assert notifications_for(client, manager) == []  # no self-notifications


def test_own_records_do_not_notify(client, rep):
    client.post("/api/deals", json={"name": "Mine"}, headers=auth_headers(rep))
    assert notifications_for(client, rep) == []


def test_won_deal_notifies_owner_and_managers(client, admin, manager, rep):
    stages = stage_ids(client, rep)
    deal = client.post("/api/deals", json={"name": "Big one", "value": 10000}, headers=auth_headers(rep)).json()
    client.patch(f"/api/deals/{deal['id']}/stage", json={"stage_id": stages["Won"]}, headers=auth_headers(rep))

    assert [n["type"] for n in notifications_for(client, manager)] == ["deal_won"]
    assert [n["type"] for n in notifications_for(client, admin)] == ["deal_won"]
    assert notifications_for(client, rep) == []  # rep moved it themselves


def test_due_task_notification_is_created_once(client, rep):
    headers = auth_headers(rep)
    client.post("/api/tasks", json={"title": "Call back", "due_date": date.today().isoformat()}, headers=headers)
    client.post("/api/tasks", json={"title": "Later", "due_date": (date.today() + timedelta(days=7)).isoformat()}, headers=headers)

    assert client.get("/api/notifications/unread-count", headers=headers).json() == {"count": 1}
    assert client.get("/api/notifications/unread-count", headers=headers).json() == {"count": 1}
    assert notifications_for(client, rep)[0]["title"] == "Task is due today: Call back"


def test_mark_read_and_read_all(client, manager, rep, other_rep):
    for name in ("A", "B"):
        client.post("/api/leads", json={"name": name, "owner_id": str(rep.id)}, headers=auth_headers(manager))
    items = notifications_for(client, rep)

    assert client.patch(f"/api/notifications/{items[0]['id']}/read", headers=auth_headers(other_rep)).status_code == 404
    assert client.patch(f"/api/notifications/{items[0]['id']}/read", headers=auth_headers(rep)).json()["is_read"]
    assert client.get("/api/notifications/unread-count", headers=auth_headers(rep)).json() == {"count": 1}

    client.post("/api/notifications/read-all", headers=auth_headers(rep))
    assert client.get("/api/notifications/unread-count", headers=auth_headers(rep)).json() == {"count": 0}


def test_audit_log_records_changes(client, manager, rep):
    headers = auth_headers(rep)
    stages = stage_ids(client, rep)
    deal = client.post("/api/deals", json={"name": "Audited", "value": 100}, headers=headers).json()
    client.patch(f"/api/deals/{deal['id']}", json={"value": 250, "name": "Audited"}, headers=headers)
    client.patch(f"/api/deals/{deal['id']}/stage", json={"stage_id": stages["Proposal"]}, headers=headers)

    logs = client.get("/api/audit-logs", params={"entity_id": deal["id"]}, headers=auth_headers(manager)).json()["items"]
    actions = [log["action"] for log in logs]
    assert sorted(actions) == ["deal.created", "deal.stage_changed", "deal.updated"]

    by_action = {log["action"]: log for log in logs}
    assert by_action["deal.updated"]["details"]["changes"] == {"value": [100.0, 250.0]}  # unchanged name not logged
    assert by_action["deal.stage_changed"]["details"]["from"] == "New"
    assert by_action["deal.stage_changed"]["details"]["to"] == "Proposal"
    assert by_action["deal.created"]["user"]["id"] == str(rep.id)


def test_lead_conversion_is_audited(client, manager, rep):
    lead = client.post("/api/leads", json={"name": "Conv"}, headers=auth_headers(rep)).json()
    client.post(f"/api/leads/{lead['id']}/convert", json={}, headers=auth_headers(rep))
    logs = client.get("/api/audit-logs", params={"action": "lead.converted"}, headers=auth_headers(manager)).json()
    assert logs["total"] == 1 and logs["items"][0]["details"]["deal_id"] is not None


def test_audit_log_is_manager_only(client, rep):
    assert client.get("/api/audit-logs", headers=auth_headers(rep)).status_code == 403
