# Environment-backed application settings.
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CSV Usage Analyzer"
    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/csv_usage_analyzer"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def async_database_url(self) -> str:
        """Return a PostgreSQL URL in the format expected by asyncpg."""
        parts = urlsplit(self.database_url)
        scheme = parts.scheme
        if scheme == "postgres":
            scheme = "postgresql"
        if scheme == "postgresql":
            scheme = "postgresql+asyncpg"

        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        if "sslmode" in query:
            query["ssl"] = query.pop("sslmode")

        return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


settings = Settings()
