from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_name: str = "NSJ Recruitment"
    database_url: str = "sqlite:///./data/sqlite/recruitment.db"
    cv_raw_dir: Path = Path("./data/cv_raw")
    cv_text_dir: Path = Path("./data/cv_text")
    export_dir: Path = Path("./data/exports")
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    dashboard_api_base_url: str = "http://127.0.0.1:8000"
    llm_provider: str = "none"
    openai_api_key: str | None = None
    openai_cv_model: str = "gpt-4o-mini"
    openai_match_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 512
    anthropic_api_key: str | None = None
    gmail_enabled: bool = False
    gmail_jobs_label: str = "משרות"
    gmail_cvs_label: str = "קורות חיים"
    gmail_lookback_days: int = 1
    gmail_include_child_labels: bool = True
    gmail_mark_processed: bool = True
    gmail_client_secret_file: Path | None = None
    gmail_token_file: Path | None = None
    outlook_enabled: bool = False
    meta_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def ensure_local_directories(self) -> None:
        for directory in (self.cv_raw_dir, self.cv_text_dir, self.export_dir):
            directory.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///./"):
            Path(self.database_url.removeprefix("sqlite:///./")).parent.mkdir(
                parents=True, exist_ok=True
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
