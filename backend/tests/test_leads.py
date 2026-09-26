from tests.conftest import auth_headers


def create_lead(client, user, **fields):
    payload = {"name": "Grace Hopper", "email": "grace@navy.mil", "company_name": "US Navy", "source": "referral", **fields}
    response = client.post("/api/leads", json=payload, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


def test_lead_crud_and_validation(client, rep):
    lead = create_lead(client, rep, score=75)
    assert lead["status"] == "new" and lead["score"] == 75 and lead["owner"]["id"] == str(rep.id)

    response = client.patch(f"/api/leads/{lead['id']}", json={"status": "qualified"}, headers=auth_headers(rep))
    assert response.json()["status"] == "qualified"

    assert client.post("/api/leads", json={"name": "X", "score": 101}, headers=auth_headers(rep)).status_code == 422
    assert client.post("/api/leads", json={"name": "X", "source": "tv"}, headers=auth_headers(rep)).status_code == 422


def test_lead_filters(client, rep):
    create_lead(client, rep, name="Low", score=10, source="website")
    create_lead(client, rep, name="High", score=90, source="referral", status="qualified")
    headers = auth_headers(rep)

    def names(**params):
        return [lead["name"] for lead in client.get("/api/leads", params=params, headers=headers).json()["items"]]

    assert names(min_score=50) == ["High"]
    assert names(source="website") == ["Low"]
    assert names(status="qualified") == ["High"]
    assert names(sort_by="score", sort_order="asc") == ["Low", "High"]


def test_cannot_set_converted_status_directly(client, rep):
    lead = create_lead(client, rep)
    response = client.patch(f"/api/leads/{lead['id']}", json={"status": "converted"}, headers=auth_headers(rep))
    assert response.status_code == 400


def test_convert_lead_creates_company_contact_and_deal(client, rep):
    lead = create_lead(client, rep)
    response = client.post(
        f"/api/leads/{lead['id']}/convert",
        json={"deal_name": "Navy compiler contract", "deal_value": "50000"},
        headers=auth_headers(rep),
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["lead"]["status"] == "converted"
    assert result["lead"]["converted_at"] is not None

    headers = auth_headers(rep)
    contact = client.get(f"/api/contacts/{result['contact_id']}", headers=headers).json()
    assert (contact["first_name"], contact["last_name"]) == ("Grace", "Hopper")
    assert contact["email"] == "grace@navy.mil"
    assert contact["company"]["id"] == result["company_id"]
    assert contact["owner"]["id"] == str(rep.id)

    company = client.get(f"/api/companies/{result['company_id']}", headers=headers).json()
    assert company["name"] == "US Navy"

    deal = client.get(f"/api/deals/{result['deal_id']}", headers=headers).json()
    assert deal["name"] == "Navy compiler contract"
    assert deal["value"] == 50000
    assert deal["stage"]["name"] == "New"
    assert deal["contact"]["name"] == "Grace Hopper"


def test_convert_links_existing_company_by_name(client, rep):
    existing = client.post("/api/companies", json={"name": "us navy"}, headers=auth_headers(rep)).json()
    lead = create_lead(client, rep)
    result = client.post(f"/api/leads/{lead['id']}/convert", json={"create_deal": False}, headers=auth_headers(rep)).json()
    assert result["company_id"] == existing["id"]
    assert result["deal_id"] is None


def test_convert_twice_returns_409(client, rep):
    lead = create_lead(client, rep)
    url = f"/api/leads/{lead['id']}/convert"
    assert client.post(url, json={}, headers=auth_headers(rep)).status_code == 200
    assert client.post(url, json={}, headers=auth_headers(rep)).status_code == 409


def test_rep_cannot_convert_someone_elses_lead(client, rep, other_rep):
    lead = create_lead(client, other_rep)
    assert client.post(f"/api/leads/{lead['id']}/convert", json={}, headers=auth_headers(rep)).status_code == 403


def test_lead_without_company(client, rep):
    lead = create_lead(client, rep, company_name=None, name="Solo")
    result = client.post(f"/api/leads/{lead['id']}/convert", json={}, headers=auth_headers(rep)).json()
    assert result["company_id"] is None
    assert client.get(f"/api/contacts/{result['contact_id']}", headers=auth_headers(rep)).json()["last_name"] is None
