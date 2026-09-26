import time
import uuid

from tests.conftest import auth_headers, make_token


def test_health_is_public(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_missing_token_returns_401(client):
    response = client.get("/api/me")
    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get("/api/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_expired_token_returns_401(client):
    token = make_token(uuid.uuid4(), exp=int(time.time()) - 10)
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_wrong_audience_returns_401(client):
    token = make_token(uuid.uuid4(), aud="anon")
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_first_user_is_provisioned_as_admin_then_sales_rep(client, rep):
    # `rep` exists already (like seeded demo users), but there's no admin yet.
    first, second = uuid.uuid4(), uuid.uuid4()

    response = client.get("/api/me", headers={"Authorization": f"Bearer {make_token(first, 'first@x.com')}"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["full_name"] == "Test User"

    response = client.get("/api/me", headers={"Authorization": f"Bearer {make_token(second, 'second@x.com')}"})
    assert response.json()["role"] == "sales_rep"


def test_deactivated_user_gets_403(client, db, rep):
    rep.is_active = False
    db.commit()
    assert client.get("/api/me", headers=auth_headers(rep)).status_code == 403


def test_update_me(client, rep):
    response = client.patch("/api/me", json={"full_name": "Riley R."}, headers=auth_headers(rep))
    assert response.status_code == 200
    assert response.json()["full_name"] == "Riley R."


def test_only_admin_can_change_roles(client, admin, manager, rep):
    url = f"/api/users/{rep.id}"
    assert client.patch(url, json={"role": "manager"}, headers=auth_headers(rep)).status_code == 403
    assert client.patch(url, json={"role": "manager"}, headers=auth_headers(manager)).status_code == 403

    response = client.patch(url, json={"role": "manager"}, headers=auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["role"] == "manager"


def test_admin_cannot_demote_self(client, admin):
    response = client.patch(f"/api/users/{admin.id}", json={"role": "sales_rep"}, headers=auth_headers(admin))
    assert response.status_code == 400


def test_invalid_role_rejected(client, admin, rep):
    response = client.patch(f"/api/users/{rep.id}", json={"role": "superuser"}, headers=auth_headers(admin))
    assert response.status_code == 422
