"""The assistant as a LangGraph agent.

    START ──▶ agent ──(tool calls?)── yes ──▶ tools ──┐
                ▲          │                          │
                │          no ──▶ END                 │
                └─────────────────────────────────────┘

`agent` asks the chat model (Gemini or Ollama, see llm.py) what to do next; `tools` runs the LangChain tools it
asked for (tools.py) and feeds the results back, until the model answers in plain text.

The server keeps no chat state: the client sends the whole conversation (including what was saved in earlier
turns) with every message.
"""

import logging
from datetime import date, timedelta

import httpx
import ollama
from langchain_core.exceptions import ModelRateLimitError, ModelTimeoutError
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import bad_gateway
from app.models import Profile
from app.schemas.assistant import ChatMessage, SavedRecord
from app.services.assistant.llm import MODEL_ERRORS, build_chat_model
from app.services.assistant.tools import TOOLS

logger = logging.getLogger("nexa_crm")

# Upper bound on model round-trips per user message (each round may call several tools).
MAX_STEPS = 10

SYSTEM_PROMPT = """You are the NexaCRM assistant for {name}. The user tells you, in their own words, about their \
sales work: new prospects, calls, emails, meetings, follow-ups. Record it accurately in the CRM with your tools, \
then confirm briefly.

Today is {today:%A, %Y-%m-%d}. Resolve relative dates ("next Tuesday") against it; write dates as YYYY-MM-DD. \
The coming days: {coming_days}.

How to record things:
- Always call search_records before creating a person or company, so you never create duplicates. Reuse an \
existing record when the name or email clearly matches.
- A new prospect who isn't a customer yet (from a cold call, cold email, referral, the website, an event…) is a \
lead. Set its source from how they came in and company_name if mentioned. Create a contact (and company) instead \
only for established relationships or when the user explicitly asks for a contact.
- Log every interaction the user describes (call, email, meeting) with log_activity, linked to the lead, contact \
or company it was with. Put what was discussed in the description.
- Turn promised follow-ups into tasks, with a due date when one is given.
- Use add_note for context that isn't an interaction: needs, budget, preferences, background.
- Update a lead when the story implies it: status "contacted" after the first real conversation, "qualified" \
when there is genuine interest or budget, "unqualified" when it's not a fit; score 0-100 for how promising it is.
- Never invent names, emails, phone numbers or facts. If you don't know a person's name, ask for it instead of \
creating a record.
- If a tool returns an error, fix the arguments and retry, or tell the user what went wrong.

Reply style: short, friendly plain text (no Markdown). After saving, sum up in one or two sentences what you \
recorded; the app shows links to the saved records, so don't list IDs. If the user is only chatting or asking a \
question, answer without saving anything. Ask at most one clarifying question at a time."""


def build_graph() -> CompiledStateGraph:
    model = build_chat_model(TOOLS)

    def agent(state: MessagesState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # → "tools" if the model called tools, else END
    graph.add_edge("tools", "agent")
    return graph.compile()


def _to_message(message: ChatMessage) -> AnyMessage:
    if message.role == "user":
        return HumanMessage(message.content)
    text = message.content
    if message.records:
        saved = "; ".join(f"{r.type} {r.action} “{r.label}” (id {r.id})" for r in message.records)
        text += f"\n\n[Saved in this turn: {saved}]"
    return AIMessage(text)


def _saved_records(messages: list[AnyMessage]) -> list[SavedRecord]:
    return [m.artifact for m in messages if isinstance(m, ToolMessage) and isinstance(m.artifact, SavedRecord)]


def _model_error_text(exc: Exception) -> str:
    if isinstance(exc, ModelRateLimitError):
        if "PerDay" in str(exc):
            return "The AI model's daily quota is used up. It resets tomorrow (or enable billing for your Gemini key)."
        return "The AI model's rate limit was reached. Please wait a minute and try again."
    if isinstance(exc, ModelTimeoutError):
        return "The AI model took too long to answer. Please try again."
    if isinstance(exc, (httpx.ConnectError, ConnectionError)) and settings.llm_provider == "ollama":
        return f"Can't reach Ollama at {settings.ollama_base_url}. Is it running?"
    if isinstance(exc, ollama.ResponseError):
        hint = f" Try: ollama pull {settings.ollama_model}" if exc.status_code == 404 else ""
        return f"Ollama returned an error: {exc.error}.{hint}"
    return "The AI model failed to respond. Please try again in a moment."


def chat(db: Session, user: Profile, messages: list[ChatMessage]) -> dict:
    graph = build_graph()
    today = date.today()
    # Small local models get weekday arithmetic wrong, so spell out the next week.
    coming_days = ", ".join(f"{day:%A} {day:%Y-%m-%d}" for day in (today + timedelta(days=n) for n in range(1, 8)))
    system = SystemMessage(SYSTEM_PROMPT.format(name=user.full_name, today=today, coming_days=coming_days))
    history = [system, *(_to_message(message) for message in messages)]
    config = {
        "configurable": {"db": db, "user": user},  # handed to the tools, never to the model
        "recursion_limit": 2 * MAX_STEPS + 1,  # each step is an agent node + a tools node
        # ToolNode runs parallel tool calls in threads by default; they share one DB session, so run them in turn.
        "max_concurrency": 1,
    }

    # Stream the graph's state after every node, so records saved before a failure can still be shown.
    state_messages = history
    try:
        for state in graph.stream({"messages": history}, config, stream_mode="values"):
            state_messages = state["messages"]
    except GraphRecursionError:
        reply = "I saved what I could, but this took too many steps. Please check the records below."
        return {"reply": reply, "records": _saved_records(state_messages)}
    except MODEL_ERRORS as exc:  # the model call failed (tools catch their own errors)
        logger.warning("Assistant model error (%s): %s", settings.llm_provider, exc)
        error = _model_error_text(exc)
        if saved := _saved_records(state_messages):  # already committed: still show them
            return {"reply": f"I saved the records below, but then hit a problem. {error}", "records": saved}
        raise bad_gateway(error)

    records = _saved_records(state_messages)
    if reply := state_messages[-1].text:
        return {"reply": reply, "records": records}
    # The model stopped without a word (small local models sometimes spend their whole budget thinking).
    if records:
        return {"reply": "I saved the records below.", "records": records}
    reply = "Sorry, I couldn't work out what to save from that. Could you try again or rephrase it?"
    return {"reply": reply, "records": []}
