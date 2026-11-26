"""The assistant's record lists and file exports (Excel, Word, PowerPoint, Markdown), with a scripted model."""

import base64
import io
from datetime import date, datetime, timedelta, timezone

import pytest
from docx import Document as WordDocument
from openpyxl import load_workbook
from pptx import Presentation

from app.db.tenancy import set_current_org
from app.models import Company, Contact, Deal, Lead
from app.models.enums import UserRole
from app.services.assistant import exports
from app.services.pipelines import get_default_pipeline
from tests.conftest import auth_headers, make_member, make_org
from tests.test_assistant import calls, last_tool_result, reply, send, use_model


def decode(file: dict) -> bytes:
    return base64.b64decode(file["content_base64"])


def workbook_rows(file: dict) -> list[tuple]:
    sheet = load_workbook(io.BytesIO(decode(file))).active
    return list(sheet.iter_rows(values_only=True))


def export(client, user, format: str, **filters):
    payload = {"filters": filters, "format": format}
    return client.post("/api/assistant/export", json=payload, headers=auth_headers(user))


@pytest.fixture
def contacts(db, rep, other_rep):
    """Three contacts by Sam (one with a formula-like name, as a web form might send) and one by Riley."""
    db.add_all(
        [
            Contact(first_name="Priya", last_name="Shah", email="priya@brightwave.io", created_by_id=other_rep.id,
                    owner_id=other_rep.id, tags=["vip"]),
            Contact(first_name="Tom", last_name="Becker", created_by_id=other_rep.id, owner_id=rep.id),
            Contact(first_name="=HYPERLINK(\"http://evil\")", created_by_id=other_rep.id, owner_id=other_rep.id),
            Contact(first_name="Lena", last_name="Fischer", created_by_id=rep.id, owner_id=rep.id),
        ]
    )
    db.commit()


def test_listing_records_offers_an_excel_export(client, rep, other_rep, contacts, monkeypatch):
    model = use_model(
        monkeypatch,
        [
            calls(("list_records", {"record_type": "contact", "created_by": "Sam"})),
            reply("Sam created 3 contacts: Priya Shah, Tom Becker and one more. Would you like this as an Excel file?"),
        ],
    )

    response = send(client, rep, "Show me all contacts created by Sam")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["records"] == [] and body["files"] == []
    offer = body["export_offer"]
    assert (offer["record_type"], offer["created_by"], offer["total"]) == ("contact", "Sam", 3)
    assert offer["label"] == "3 contacts created by Sam Rep"

    listing = last_tool_result(model.calls[1])
    assert listing["total"] == 3 and listing["showing"] == 3
    assert {row["Name"] for row in listing["rows"]} == {"Priya Shah", "Tom Becker", '=HYPERLINK("http://evil")'}
    assert all("id" in row and "Email" not in row for row in listing["rows"] if row["Name"] == "Tom Becker")
    assert "Excel" in listing["next_step"]  # nudges the model to offer the file
    assert "Excel" in model.calls[0][0].content  # and so does the system prompt


def test_list_filters(client, db, rep, other_rep, contacts, monkeypatch):
    old = Lead(name="Old Lead", source="website", status="qualified", owner_id=rep.id)
    db.add_all(
        [
            old,
            Lead(name="Web Lead", source="website", status="new", owner_id=rep.id),
            Lead(name="Call Lead", source="cold_call", status="qualified", owner_id=other_rep.id),
        ]
    )
    db.commit()
    old.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    db.commit()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    model = use_model(
        monkeypatch,
        [
            calls(("list_records", {"record_type": "lead", "source": "website", "owner": "me"})),
            calls(("list_records", {"record_type": "lead", "status": "Qualified"})),
            calls(("list_records", {"record_type": "lead", "created_from": week_ago})),
            calls(("list_records", {"record_type": "contact", "owner": "riley", "search": "becker"})),
            calls(("list_records", {"record_type": "lead", "status": "won"})),
            calls(("list_records", {"record_type": "contact", "source": "website"})),
            calls(("list_records", {"record_type": "contact", "created_by": "Nobody"})),
            calls(("list_records", {"record_type": "contact", "created_by": "Rep"})),
            reply("Done"),
        ],
    )

    assert send(client, rep, "Run some lists").status_code == 200

    def names(step: int) -> set[str]:
        return {row["Name"] for row in last_tool_result(model.calls[step])["rows"]}

    assert names(1) == {"Old Lead", "Web Lead"}
    assert names(2) == {"Old Lead", "Call Lead"}  # status matched case-insensitively
    assert names(3) == {"Web Lead", "Call Lead"}
    assert names(4) == {"Tom Becker"}
    assert "Use one of: new, contacted" in last_tool_result(model.calls[5])["error"]
    assert last_tool_result(model.calls[6])["error"] == "Only leads have a source."
    assert "No team member matches 'Nobody'. The team: Riley Rep, Sam Rep." in last_tool_result(model.calls[7])["error"]
    assert "matches several team members: Riley Rep, Sam Rep" in last_tool_result(model.calls[8])["error"]


def test_lists_companies_and_contacts_by_location(client, db, rep, monkeypatch):
    db.add_all(
        [
            Company(name="Wells Fargo", city="Mumbai", country="India"),
            Company(name="Navi Labs", city="Navi Mumbai", country="India"),
            Company(name="Pawai Tech", address="Saki Vihar Road, Mumbai"),  # city left empty
            Company(name="Pune Soft", city="Pune", country="India"),
            Contact(first_name="Aditya", city="Mumbai"),
            Contact(first_name="Riya", city="Delhi"),
        ]
    )
    db.commit()
    model = use_model(
        monkeypatch,
        [
            calls(("list_records", {"record_type": "company", "location": "mumbai"})),
            calls(("list_records", {"record_type": "contact", "location": "Mumbai"})),
            calls(("list_records", {"record_type": "lead", "location": "Mumbai"})),
            reply("3 companies are in Mumbai. Would you like this as an Excel file?"),
        ],
    )

    response = send(client, rep, "give me list of the companies that are located in mumbai")

    assert response.status_code == 200, response.text
    companies = last_tool_result(model.calls[1])
    assert {row["Name"] for row in companies["rows"]} == {"Wells Fargo", "Navi Labs", "Pawai Tech"}
    assert companies["found"] == "3 companies in mumbai"
    assert [row["Name"] for row in last_tool_result(model.calls[2])["rows"]] == ["Aditya"]
    assert last_tool_result(model.calls[3])["error"] == "Only companies and contacts have a location."
    assert "located in Mumbai" in model.calls[0][0].content  # the prompt maps places to the filter

    offer = response.json()["export_offer"]  # the last list run (contacts) is what the buttons export
    rows = workbook_rows(export(client, rep, "xlsx", **{k: offer[k] for k in ("record_type", "location")}).json())
    assert [row[0] for row in rows[1:]] == ["Aditya"]


def test_saying_yes_exports_the_list_to_excel(client, rep, other_rep, contacts, monkeypatch):
    offer = {"record_type": "contact", "created_by": "Sam", "total": 3, "label": "3 contacts created by Sam Rep"}
    history = [
        {"role": "user", "content": "Show me all contacts created by Sam"},
        {"role": "assistant", "content": "Sam created 3 contacts. Would you like this as an Excel file?",
         "export_offer": offer},
    ]
    model = use_model(
        monkeypatch,
        [
            calls(("export_records", {"format": "xlsx", "record_type": "contact", "created_by": "Sam"})),
            reply("Your Excel file is ready."),
        ],
    )

    response = send(client, rep, "Yes", history)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"] == "Your Excel file is ready." and body["export_offer"] is None
    [file] = body["files"]
    assert file["filename"] == "contacts-created-by-sam-rep.xlsx" and file["format"] == "xlsx"
    rows = workbook_rows(file)
    assert rows[0][:3] == ("Name", "Company", "Email")
    assert {row[0] for row in rows[1:]} == {"Priya Shah", "Tom Becker", '=HYPERLINK("http://evil")'}
    priya = next(row for row in rows if row[0] == "Priya Shah")
    assert priya[8] == "vip" and priya[9] == "Sam Rep" and priya[10] == "Sam Rep"  # tags, owner, created by
    # The earlier list's filters went back to the model, so "yes" can reuse them.
    assert '"created_by": "Sam"' in model.calls[0][2].content
    assert last_tool_result(model.calls[1]) == {"file": file["filename"], "ready": True}


def test_excel_never_runs_crm_text_as_a_formula(client, rep, contacts):
    response = export(client, rep, "xlsx", record_type="contact")
    assert response.status_code == 200, response.text
    sheet = load_workbook(io.BytesIO(decode(response.json()))).active
    cell = next(row[0] for row in sheet.iter_rows(min_row=2) if str(row[0].value).startswith("="))
    assert cell.data_type == "s"


def test_export_endpoint_makes_every_format(client, db, rep, contacts):
    db.add(Deal(name="Big deal", value=12500, pipeline_id=(p := get_default_pipeline(db)).id, stage_id=p.stages[0].id))
    db.commit()

    xlsx = export(client, rep, "xlsx", record_type="deal").json()
    assert workbook_rows(xlsx)[1][:5] == ("Big deal", None, 12500, "USD", "New")

    docx = export(client, rep, "docx", record_type="contact", owner="Riley").json()
    assert docx["mime_type"].endswith("wordprocessingml.document")
    word = WordDocument(io.BytesIO(decode(docx)))
    assert word.paragraphs[0].text == "Contacts owned by Riley Rep"
    assert sorted(row.cells[0].text for row in word.tables[0].rows) == ["Lena Fischer", "Name", "Tom Becker"]

    pptx = export(client, rep, "pptx", record_type="contact").json()
    deck = Presentation(io.BytesIO(decode(pptx)))
    assert deck.slides[0].shapes.title.text == "Contacts"
    table = next(shape for shape in deck.slides[1].shapes if shape.has_table).table
    assert len(table.columns) == exports.SLIDE_COLUMNS and len(table.rows) == 5

    md = decode(export(client, rep, "md", record_type="contact", search="priya").json()).decode()
    assert md.startswith("# Contacts matching “priya”")
    assert "| Priya Shah |  | priya@brightwave.io |" in md


def test_export_endpoint_rejects_bad_filters(client, rep, contacts):
    response = export(client, rep, "xlsx", record_type="company", status="active")
    assert response.status_code == 400 and response.json()["detail"] == "Companies have no status."
    assert export(client, rep, "pdf", record_type="contact").status_code == 422


def test_lists_and_exports_stay_in_the_organization(client, db, rep, contacts):
    other_org = make_org(db, "Globex")
    outsider = make_member(db, other_org, UserRole.ADMIN, "Olga Outsider")
    set_current_org(db, other_org.id)
    db.add(Contact(first_name="Hidden", created_by_id=outsider.id))
    db.commit()

    rows = workbook_rows(export(client, rep, "xlsx", record_type="contact").json())
    assert "Hidden" not in {row[0] for row in rows} and len(rows) == 5
    response = export(client, rep, "xlsx", record_type="contact", created_by="Olga")
    assert response.status_code == 400 and "No team member matches 'Olga'" in response.json()["detail"]


def test_long_tables_are_cut_with_a_note(monkeypatch, client, rep, contacts):
    monkeypatch.setitem(exports.ROW_LIMITS, "docx", 2)
    word = WordDocument(io.BytesIO(decode(export(client, rep, "docx", record_type="contact").json())))
    assert len(word.tables[0].rows) == 3
    assert word.paragraphs[-1].text == "Showing the first 2 of 4 rows. Export to Excel for the full list."


def test_assistant_writes_documents(client, rep, monkeypatch):
    sections = [
        {"heading": "Overview", "paragraphs": ["Acme is a manufacturing account."], "bullets": ["Budget approved"]},
        {"heading": "Deals", "table": {"columns": ["Deal", "Value"], "rows": [["Rollout", "5,000"]]}},
    ]
    document = {"title": "Acme account overview", "sections": sections}
    model = use_model(
        monkeypatch,
        [
            calls(
                ("export_document", {"format": "docx", **document}),
                ("export_document", {"format": "pptx", **document, "subtitle": "For the QBR"}),
                ("export_document", {"format": "md", **document}),
                ("export_document", {"format": "xlsx", "title": "Notes", "sections": [{"paragraphs": ["Hi"]}]}),
            ),
            reply("Your files are ready."),
        ],
    )

    response = send(client, rep, "Yes, as Word, PowerPoint and Markdown")

    assert response.status_code == 200, response.text
    files = response.json()["files"]
    assert [f["filename"] for f in files] == ["acme-account-overview.docx", "acme-account-overview.pptx",
                                              "acme-account-overview.md"]
    word = WordDocument(io.BytesIO(decode(files[0])))
    assert [p.text for p in word.paragraphs[:4]] == [
        "Acme account overview", "Overview", "Acme is a manufacturing account.", "Budget approved"
    ]
    assert word.tables[0].rows[1].cells[0].text == "Rollout"
    deck = Presentation(io.BytesIO(decode(files[1])))
    assert [s.shapes.title.text for s in deck.slides] == ["Acme account overview", "Overview", "Deals"]
    assert deck.slides[0].placeholders[1].text == "For the QBR"
    assert "| Rollout | 5,000 |" in decode(files[2]).decode()
    assert "needs a table" in last_tool_result(model.calls[1])["error"]
    # Files made earlier go back to the model by name.
    history = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "Ready", "files": ["a.docx"]}]
    model = use_model(monkeypatch, [reply("Ok")])
    send(client, rep, "Thanks", history)
    assert "[Files made in this turn: a.docx]" in model.calls[0][2].content
