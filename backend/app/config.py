from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "DriftSense"
    APP_VERSION: str = "0.1.0"
    BACKEND_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-me"

    DATABASE_URL: str = "postgresql+psycopg2://driftsense:driftsense_password@localhost:5432/driftsense"

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = str(PROJECT_ROOT / "data" / "uploads")

    LLM_PROVIDER: str = "none"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def storage_path_resolved(self) -> Path:
        path = Path(self.STORAGE_LOCAL_PATH)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
