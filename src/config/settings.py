from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_api_base_url: str = Field(default="https://api.github.com", alias="GITHUB_API_BASE_URL")
    request_timeout_seconds: float = Field(default=20.0, alias="REQUEST_TIMEOUT_SECONDS")
    max_file_size_bytes: int = Field(default=200_000, alias="MAX_FILE_SIZE_BYTES", ge=1)
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    output_dir: Path = Field(default=Path("outputs"), alias="OUTPUT_DIR")
    tree_analysis_model: str = Field(default="gemini/gemini-2.5-flash", alias="TREE_ANALYSIS_MODEL")
    repository_analysis_model: str = Field(
        default="gemini/gemini-2.5-flash",
        alias="REPOSITORY_ANALYSIS_MODEL",
    )

    # ✅ ADD THIS
    GEMINI_API_KEY: str | None = Field(default=None, alias="GEMINI_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
