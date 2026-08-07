"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──
    app_name: str = "AI Comic Studio"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    secret_key: str = "change-me-in-production-use-a-random-string"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database ──
    database_url: str = "postgresql+asyncpg://comic:comic123@localhost:5432/comic_studio"
    database_url_sync: str = "postgresql://comic:comic123@localhost:5432/comic_studio"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── MinIO / S3 ──
    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "comic-studio"
    s3_secure: bool = False
    s3_public_url: str = "http://localhost:9000/comic-studio"

    # ── LLM ──
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-20251001"

    # ── Image Generation ──
    image_provider: Literal["openai", "dalle", "stable_diffusion", "flux"] = "openai"
    image_model: str = "dall-e-3"
    image_concurrency: int = 4

    # ── Video Generation ──
    video_provider: str = ""
    video_model: str = ""
    video_concurrency: int = 2

    # ── TTS ──
    tts_provider: str = "openai"
    tts_model: str = "tts-1-hd"
    tts_default_voice: str = "alloy"
    tts_concurrency: int = 2

    # ── Budget ──
    max_budget_per_project_usd: float = 50.0
    budget_mode: Literal["observe", "warn", "cap"] = "warn"

    # ── Paths ──
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")
    generated_dir: Path = Path("./generated")

    # ── Auth ──
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30


settings = Settings()
