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
    secret_key: str | None = Field(default=None, alias="SECRET_KEY")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_endpoint_url: str | None = Field(default=None, alias="AWS_ENDPOINT_URL")
    aws_public_endpoint_url: str | None = Field(default=None, alias="AWS_PUBLIC_ENDPOINT_URL")
    s3_bucket_name: str | None = Field(default=None, alias="S3_BUCKET_NAME")
    s3_presign_expires_seconds: int = Field(
        default=900,
        alias="S3_PRESIGN_EXPIRES_SECONDS",
        ge=60,
        le=86_400,
    )
    sqs_queue_url: str | None = Field(default=None, alias="SQS_QUEUE_URL")
    ses_sender_email: str | None = Field(default=None, alias="SES_SENDER_EMAIL")
    frontend_url: str | None = Field(default=None, alias="FRONTEND_URL")
    cors_allowed_origins_csv: str | None = Field(default=None, alias="CORS_ALLOWED_ORIGINS")
    cognito_user_pool_id: str | None = Field(default=None, alias="COGNITO_USER_POOL_ID")
    cognito_client_id: str | None = Field(default=None, alias="COGNITO_CLIENT_ID")
    worker_poll_wait_seconds: int = Field(default=20, alias="WORKER_POLL_WAIT_SECONDS", ge=1, le=20)
    worker_idle_sleep_seconds: float = Field(default=2.0, alias="WORKER_IDLE_SLEEP_SECONDS", ge=0)
    worker_max_messages: int = Field(default=5, alias="WORKER_MAX_MESSAGES", ge=1, le=10)
    worker_enable_ppt_analysis: bool = Field(default=True, alias="WORKER_ENABLE_PPT_ANALYSIS")
    worker_enable_repository_analysis: bool = Field(
        default=True,
        alias="WORKER_ENABLE_REPOSITORY_ANALYSIS",
    )

    GEMINI_API_KEY: str | None = Field(default=None, alias="GEMINI_API_KEY")
    elevenlabs_api_key: str | None = Field(default=None, alias="ELEVENLABS_API_KEY")

    @property
    def cors_allowed_origins(self) -> list[str]:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        if self.frontend_url:
            origins.append(self.frontend_url)
        if self.cors_allowed_origins_csv:
            origins.extend(
                origin.strip()
                for origin in self.cors_allowed_origins_csv.split(",")
                if origin.strip()
            )
        return list(dict.fromkeys(origins))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
