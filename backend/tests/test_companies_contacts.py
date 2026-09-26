from tests.conftest import auth_headers


def create_company(client, user, **fields):
    payload = {"name": "Acme Corp", "industry": "Software", **fields}
    response = client.post("/api/companies", json=payload, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


def create_contact(client, user, **fields):
    payload = {"first_name": "Jane", "last_name": "Doe", "email": "jane@acme.com", **fields}
    response = client.post("/api/contacts", json=payload, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


# --- Companies -------------------------------------------------------------


def test_create_and_get_company(client, rep):
    company = create_company(client, rep, email="", website="acme.com")
    assert company["owner"]["id"] == str(rep.id)
    assert company["email"] is None  # blank strings become null

    response = client.get(f"/api/companies/{company['id']}", headers=auth_headers(rep))
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"


def test_company_validation(client, rep):
    response = client.post("/api/companies", json={"name": ""}, headers=auth_headers(rep))
    assert response.status_code == 422
    response = client.post("/api/companies", json={"name": "X", "email": "nope"}, headers=auth_headers(rep))
    assert response.status_code == 422


def test_company_not_found(client, rep):
    response = client.get("/api/companies/00000000-0000-0000-0000-000000000000", headers=auth_headers(rep))
    assert response.status_code == 404


def test_company_contact_count(client, rep):
    company = create_company(client, rep)
    create_contact(client, rep, company_id=company["id"])
    create_contact(client, rep, company_id=company["id"], first_name="John")
    response = client.get(f"/api/companies/{company['id']}", headers=auth_headers(rep))
    assert response.json()["contact_count"] == 2


def test_company_search_filter_sort_and_pagination(client, rep):
    for name, industry in [("Zeta Labs", "Biotech"), ("Alpha Inc", "Software"), ("Beta LLC", "Software")]:
        create_company(client, rep, name=name, industry=industry)
    headers = auth_headers(rep)

    response = client.get("/api/companies", params={"search": "alp"}, headers=headers).json()
    assert [c["name"] for c in response["items"]] == ["Alpha Inc"]

    response = client.get(
        "/api/companies", params={"industry": "Software", "sort_by": "name", "sort_order": "asc"}, headers=headers
    ).json()
    assert [c["name"] for c in response["items"]] == ["Alpha Inc", "Beta LLC"]

    response = client.get("/api/companies", params={"page_size": 2, "page": 2}, headers=headers).json()
    assert response["total"] == 3 and response["pages"] == 2 and len(response["items"]) == 1


def test_invalid_sort_field_rejected(client, rep):
    response = client.get("/api/companies", params={"sort_by": "password"}, headers=auth_headers(rep))
    assert response.status_code == 400


# --- Permissions -------------------------------------------------------------


def test_rep_cannot_edit_someone_elses_record(client, rep, other_rep):
    company = create_company(client, other_rep)
    response = client.patch(f"/api/companies/{company['id']}", json={"name": "Hijacked"}, headers=auth_headers(rep))
    assert response.status_code == 403


def test_rep_can_edit_own_record(client, rep):
    company = create_company(client, rep)
    response = client.patch(f"/api/companies/{company['id']}", json={"city": "Berlin"}, headers=auth_headers(rep))
    assert response.status_code == 200
    assert response.json()["city"] == "Berlin"


def test_rep_cannot_assign_or_reassign(client, rep, other_rep):
    response = client.post(
        "/api/companies", json={"name": "X", "owner_id": str(other_rep.id)}, headers=auth_headers(rep)
    )
    assert response.status_code == 403

    company = create_company(client, rep)
    response = client.patch(
        f"/api/companies/{company['id']}", json={"owner_id": str(other_rep.id)}, headers=auth_headers(rep)
    )
    assert response.status_code == 403


def test_manager_can_reassign_and_delete(client, manager, rep):
    company = create_company(client, rep)
    response = client.patch(
        f"/api/companies/{company['id']}", json={"owner_id": str(manager.id)}, headers=auth_headers(manager)
    )
    assert response.status_code == 200
    assert response.json()["owner"]["id"] == str(manager.id)

    assert client.delete(f"/api/companies/{company['id']}", headers=auth_headers(manager)).status_code == 204
    assert client.get(f"/api/companies/{company['id']}", headers=auth_headers(manager)).status_code == 404


def test_rep_cannot_delete(client, rep):
    company = create_company(client, rep)
    assert client.delete(f"/api/companies/{company['id']}", headers=auth_headers(rep)).status_code == 403


# --- Contacts ------------------------------------------------------------------


def test_contact_crud(client, rep):
    company = create_company(client, rep)
    contact = create_contact(client, rep, company_id=company["id"], tags=["VIP", " vip ", "partner", ""])
    assert contact["full_name"] == "Jane Doe"
    assert contact["company"] == {"id": company["id"], "name": "Acme Corp"}
    assert contact["tags"] == ["VIP", "partner"]

    response = client.patch(
        f"/api/contacts/{contact['id']}", json={"status": "customer", "job_title": "CTO"}, headers=auth_headers(rep)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "customer"
    assert response.json()["job_title"] == "CTO"


def test_contact_invalid_company_rejected(client, rep):
    response = client.post(
        "/api/contacts",
        json={"first_name": "A", "company_id": "00000000-0000-0000-0000-000000000000"},
        headers=auth_headers(rep),
    )
    assert response.status_code == 400


def test_contact_invalid_status_rejected(client, rep):
    response = client.post("/api/contacts", json={"first_name": "A", "status": "vip"}, headers=auth_headers(rep))
    assert response.status_code == 422


def test_contact_filters(client, rep, other_rep):
    company = create_company(client, rep)
    create_contact(client, rep, first_name="Ann", company_id=company["id"], tags=["vip"], status="customer")
    create_contact(client, rep, first_name="Bob", email="bob@x.com")
    create_contact(client, other_rep, first_name="Cid", email="cid@x.com")
    headers = auth_headers(rep)

    def names(**params):
        items = client.get("/api/contacts", params=params, headers=headers).json()["items"]
        return sorted(c["first_name"] for c in items)

    assert names(search="bob@") == ["Bob"]
    assert names(search="ann doe") == ["Ann"]
    assert names(status="customer") == ["Ann"]
    assert names(company_id=company["id"]) == ["Ann"]
    assert names(tag="vip") == ["Ann"]
    assert names(owner_id=str(other_rep.id)) == ["Cid"]
    assert client.get("/api/contacts/tags", headers=headers).json() == ["vip"]


def test_deleting_company_keeps_contacts(client, manager):
    company = create_company(client, manager)
    contact = create_contact(client, manager, company_id=company["id"])
    client.delete(f"/api/companies/{company['id']}", headers=auth_headers(manager))
    response = client.get(f"/api/contacts/{contact['id']}", headers=auth_headers(manager))
    assert response.status_code == 200
    assert response.json()["company"] is None
