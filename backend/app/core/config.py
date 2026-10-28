from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NexaCRM API"
    database_url: str = "postgresql+psycopg://nexa:nexa@localhost:5433/nexa_crm"

    # Supabase Auth. SUPABASE_URL is used to fetch the JWKS (public signing keys).
    # SUPABASE_JWT_SECRET is only needed for projects still on legacy HS256 keys.
    supabase_url: str = ""
    supabase_jwt_secret: str = ""

    # Comma-separated list, e.g. "http://localhost:3000,https://crm.example.com"
    cors_origins: str = "http://localhost:3000"

    # AI assistant (/api/assistant): which chat model answers. "gemini" (Google, needs an API key) or "ollama" (local).
    llm_provider: Literal["gemini", "ollama"] = "gemini"

    # Google Gemini. Get a key at https://aistudio.google.com/apikey.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"  # fast, and the free tier allows far more requests than Flash
    # Tried when the main model is overloaded or out of quota. Empty disables it.
    gemini_fallback_model: str = "gemini-3.5-flash"

    # Ollama (https://ollama.com), after `ollama pull <model>`.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Hosts like Render hand out postgres:// or postgresql:// URLs; point them at the installed psycopg 3 driver."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
