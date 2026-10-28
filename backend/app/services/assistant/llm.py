"""The chat model behind the assistant, chosen in backend/.env:

    LLM_PROVIDER=gemini   Google Gemini (GEMINI_API_KEY, GEMINI_MODEL, optional GEMINI_FALLBACK_MODEL)
    LLM_PROVIDER=ollama   a local model served by Ollama (OLLAMA_BASE_URL, OLLAMA_MODEL, e.g. qwen3:4b)

Both are LangChain chat models, so the rest of the assistant doesn't care which one it talks to.
"""

import httpx
import ollama
from langchain_core.exceptions import (
    ModelAPIError,
    ModelConnectionError,
    ModelError,
    ModelRateLimitError,
    ModelTimeoutError,
)
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.core.exceptions import service_unavailable

# Failures worth retrying on another model. Quotas are per model, so a rate limit counts too.
FALLBACK_ON = (ModelRateLimitError, ModelAPIError, ModelTimeoutError, ModelConnectionError)
# Everything a model call can fail with (Ollama talks plain HTTP through its own client).
MODEL_ERRORS = (ModelError, ChatGoogleGenerativeAIError, ollama.ResponseError, httpx.HTTPError, ConnectionError)


def _gemini(model: str) -> BaseChatModel:
    # One quick retry and a 40s cap: we'd rather switch to the fallback model or tell the user than hang.
    return ChatGoogleGenerativeAI(model=model, google_api_key=settings.gemini_api_key, max_retries=1, timeout=40)


def _ollama() -> BaseChatModel:
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        # Qwen3 "thinks" before answering by default; off is much faster on a local machine.
        reasoning=False,
        # Ollama's default context window is too small for the prompt, tool schemas and chat history.
        num_ctx=8192,
        temperature=0,
    )


def build_chat_model(tools: list[BaseTool]) -> Runnable[LanguageModelInput, AIMessage]:
    """The configured chat model with the assistant's tools bound to it."""
    if settings.llm_provider == "ollama":
        return _ollama().bind_tools(tools)

    if not settings.gemini_api_key:
        raise service_unavailable("The AI assistant isn't configured. Add GEMINI_API_KEY to backend/.env.")
    model = _gemini(settings.gemini_model).bind_tools(tools)
    fallback = settings.gemini_fallback_model
    if fallback and fallback != settings.gemini_model:
        model = model.with_fallbacks([_gemini(fallback).bind_tools(tools)], exceptions_to_handle=FALLBACK_ON)
    return model
