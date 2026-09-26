from functools import lru_cache

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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
