from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"


def normalize_database_url(url: str) -> str:
    """Ajusta formatos comuns de DATABASE_URL (Supabase, Render, etc.)."""
    normalized = url.strip().strip('"').strip("'")

    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+psycopg://", 1)
    elif normalized.startswith("postgresql://") and "+psycopg" not in normalized:
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    if "supabase.co" in normalized or "pooler.supabase.com" in normalized:
        if "sslmode=" not in normalized:
            sep = "&" if "?" in normalized else "?"
            normalized = f"{normalized}{sep}sslmode=require"

    return normalized


class Settings(BaseSettings):
    APP_NAME: str = "Zola Serviços API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    FRONTEND_ORIGIN: str
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "zola-uploads"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return normalize_database_url(self.DATABASE_URL)

    @property
    def public_api_base_url(self) -> str:
        return self.PUBLIC_API_BASE_URL.strip().rstrip("/")

    @property
    def supabase_storage_configured(self) -> bool:
        return bool(self.SUPABASE_URL.strip() and self.SUPABASE_SERVICE_ROLE_KEY.strip())


settings = Settings()
