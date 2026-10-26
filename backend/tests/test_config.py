import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "url",
    [
        "postgres://u:p@dpg-abc.oregon-postgres.render.com/nexa",
        "postgresql://u:p@dpg-abc.oregon-postgres.render.com/nexa",
        "postgresql+psycopg://u:p@dpg-abc.oregon-postgres.render.com/nexa",
    ],
)
def test_database_url_uses_psycopg_driver(url):
    # Render's dashboard gives postgres:// / postgresql:// URLs; they must work unchanged.
    settings = Settings(database_url=url)
    assert settings.database_url == "postgresql+psycopg://u:p@dpg-abc.oregon-postgres.render.com/nexa"
