"""The AI assistant (LangGraph agent), with the chat model replaced by a scripted fake."""

import json
from typing import Any

from langchain_core.exceptions import ModelAPIError, ModelRateLimitError
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from pydantic import Field

from app.core.config import settings
from app.models import Activity, AuditLog, Lead, Task
from app.services.assistant import llm
from tests.conftest import auth_headers


class ScriptedModel(BaseChatModel):
    """Plays back one step per model call. A step is a callable(messages) -> AIMessage, or raises."""

    steps: list[Any]
    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.calls.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.steps.pop(0)(messages))])


def reply(text: str):
    return lambda _messages: AIMessage(text)


def tool_calls(*requested: tuple[str, dict]) -> AIMessage:
    return AIMessage(
        "", tool_calls=[{"name": name, "args": args, "id": f"call-{name}", "type": "tool_call"} for name, args in requested]
    )


def calls(*requested: tuple[str, dict]):
    return lambda _messages: tool_calls(*requested)


def fail(error: Exception):
    def step(_messages):
        raise error

    return step


def last_tool_result(messages: list[BaseMessage]) -> dict:
    return json.loads(messages[-1].content)


def use_gemini(monkeypatch, **models: list) -> dict[str, ScriptedModel]:
    """Fake Gemini models by name: the first is the main model, the second (if any) the fallback."""
    fakes = {name: ScriptedModel(steps=steps) for name, steps in models.items()}
    names = list(fakes)
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_model", names[0])
    monkeypatch.setattr(settings, "gemini_fallback_model", names[1] if len(names) > 1 else "")
    monkeypatch.setattr(llm, "_gemini", lambda model: fakes[model])
    return fakes


def use_model(monkeypatch, steps: list) -> ScriptedModel:
    return use_gemini(monkeypatch, main=steps)["main"]


def send(client, user, text, history=()):
    messages = [*history, {"role": "user", "content": text}]
    return client.post("/api/assistant/chat", json={"messages": messages}, headers=auth_headers(user))


def test_chat_creates_lead_activity_and_task(client, db, rep, monkeypatch):
    model = use_model(
        monkeypatch,
        [
            calls(("search_records", {"query": "Jane Doe"})),
            calls(("create_lead", {"name": "Jane Doe", "company_name": "Acme", "source": "cold_call"})),
            lambda messages: tool_calls(
                (
                    "log_activity",
                    {
                        "type": "call",
                        "subject": "Cold call",
                        "description": "Interested in the Pro plan",
                        "lead_id": last_tool_result(messages)["lead_id"],
                    },
                ),
                ("create_task", {"title": "Send Jane Doe a proposal", "due_date": "2026-11-02", "priority": "high"}),
            ),
            reply("Saved Jane as a lead and logged the call."),
        ],
    )

    response = send(client, rep, "Cold-called Jane Doe from Acme, she wants a proposal by Monday")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"] == "Saved Jane as a lead and logged the call."
    assert [(r["type"], r["action"]) for r in body["records"]] == [
        ("lead", "created"),
        ("activity", "created"),
        ("task", "created"),
    ]

    lead = db.get(Lead, body["records"][0]["id"])
    assert (lead.source, lead.company_name, lead.owner_id) == ("cold_call", "Acme", rep.id)
    activity = db.get(Activity, body["records"][1]["id"])
    assert activity.lead_id == lead.id and activity.owner_id == rep.id
    assert body["records"][1]["link_type"] == "lead" and body["records"][1]["link_id"] == str(lead.id)
    assert db.get(Task, body["records"][2]["id"]).priority == "high"
    assert db.query(AuditLog).filter_by(action="lead.created", entity_id=lead.id).count() == 1

    # The system prompt went first, and both results of the parallel tool call came back before the final answer.
    final_request = model.calls[-1]
    assert final_request[0].type == "system" and "Riley Rep" in final_request[0].content
    assert [m.type for m in final_request[-2:]] == ["tool", "tool"]


def test_tool_errors_are_returned_to_the_model(client, db, rep, monkeypatch):
    model = use_model(
        monkeypatch,
        [
            calls(("create_lead", {"name": "Bob", "email": "not-an-email"})),
            calls(("log_activity", {"type": "call", "subject": "Call"})),
            calls(("create_lead", {"name": "Bob", "score": 150})),
            reply("What's Bob's email?"),
        ],
    )

    response = send(client, rep, "Add Bob")

    assert response.status_code == 200, response.text
    assert response.json()["records"] == []
    assert "email" in last_tool_result(model.calls[1])["error"]
    assert "at least one" in last_tool_result(model.calls[2])["error"]
    assert "less than or equal to 100" in model.calls[3][-1].content  # rejected by the tool's own schema
    assert db.query(Lead).filter_by(name="Bob").count() == 0


def test_reps_cannot_update_other_reps_leads_via_chat(client, db, rep, other_rep, monkeypatch):
    lead = Lead(name="Theirs", owner_id=other_rep.id)
    db.add(lead)
    db.commit()
    model = use_model(
        monkeypatch,
        [
            calls(("update_lead", {"lead_id": str(lead.id), "status": "qualified"})),
            reply("You can't edit that lead."),
        ],
    )

    assert send(client, rep, "Mark Theirs as qualified").status_code == 200
    assert "assigned to you" in last_tool_result(model.calls[1])["error"]
    db.refresh(lead)
    assert lead.status == "new"


def test_history_includes_previously_saved_records(client, rep, monkeypatch):
    model = use_model(monkeypatch, [reply("Ok")])
    record = {"type": "lead", "action": "created", "id": "8d6b2f0e-2c43-4a8e-9a39-3f1b8f6f0a11", "label": "Jane"}
    history = [
        {"role": "user", "content": "Add Jane"},
        {"role": "assistant", "content": "Done", "records": [record]},
    ]

    assert send(client, rep, "Add a note to her", history).status_code == 200
    assert [m.type for m in model.calls[0]] == ["system", "human", "ai", "human"]
    assert record["id"] in model.calls[0][2].content


def test_overloaded_or_rate_limited_model_falls_back(client, rep, monkeypatch):
    quota = ModelRateLimitError("429 quota")
    fakes = use_gemini(
        monkeypatch,
        # The main model is tried first on every step.
        main=[fail(ModelAPIError("503 overloaded")), fail(quota), fail(quota)],
        backup=[calls(("search_records", {"query": "Jane"})), reply("No Jane yet."), reply("Hi!")],
    )

    assert send(client, rep, "Do I have Jane?").json()["reply"] == "No Jane yet."
    assert send(client, rep, "Hello").json()["reply"] == "Hi!"
    assert len(fakes["main"].calls) == 3 and len(fakes["backup"].calls) == 3


def test_model_failure_keeps_already_saved_records(client, rep, monkeypatch):
    daily_quota = ModelRateLimitError("429 quota GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    use_model(monkeypatch, [calls(("create_lead", {"name": "Jane Doe"})), fail(daily_quota)])

    response = send(client, rep, "Add Jane Doe")

    assert response.status_code == 200, response.text
    assert "daily quota" in response.json()["reply"]
    assert [r["label"] for r in response.json()["records"]] == ["Jane Doe"]

    use_model(monkeypatch, [fail(ModelRateLimitError("429 per minute"))])
    response = send(client, rep, "Hello")
    assert response.status_code == 502 and "rate limit" in response.json()["detail"]


def test_ollama_provider_needs_no_gemini_key(client, rep, monkeypatch):
    fake = ScriptedModel(steps=[reply("Hi from Qwen")])
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(llm, "_ollama", lambda: fake)

    response = send(client, rep, "Hello")

    assert response.status_code == 200, response.text
    assert response.json()["reply"] == "Hi from Qwen"


def test_models_are_configured_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "ollama_model", "qwen3:4b")
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama.local:11434")
    ollama_model = llm._ollama()
    assert isinstance(ollama_model, ChatOllama)
    assert (ollama_model.model, ollama_model.base_url) == ("qwen3:4b", "http://ollama.local:11434")

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    gemini_model = llm._gemini("gemini-3.5-flash-lite")
    assert isinstance(gemini_model, ChatGoogleGenerativeAI) and gemini_model.model.endswith("gemini-3.5-flash-lite")


def test_chat_requires_gemini_key_and_a_user_message(client, rep, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert send(client, rep, "Hello").status_code == 503

    only_assistant = {"messages": [{"role": "assistant", "content": "Hi"}]}
    assert client.post("/api/assistant/chat", json=only_assistant, headers=auth_headers(rep)).status_code == 422
    assert client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": "x"}]}).status_code == 401
