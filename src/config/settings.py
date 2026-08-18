from functools import lru_cache
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    ENV: str = "dev"
    PROJECT_NAME: str = "On-Prem AI Code Platform"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # PostgreSQL Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_secret"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "code_assistant_db"
    DATABASE_URL: str | None = None

    # Redis Stack
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str | None = None

    # LiteLLM & vLLM Inference
    LITELLM_URL: str = "http://litellm:4000"
    LITELLM_MASTER_KEY: str = "sk-master-admin-key"
    DEFAULT_CODE_MODEL: str = "qwen-coder"
    SYSTEM_PROMPT: str = (
        "You are an expert AI software architect and coding assistant. "
        "Provide direct, high-performance, and secure code solutions with concise explanations."
    )

    # Hugging Face
    HF_TOKEN: str | None = None
    HF_ENDPOINT: str | None = None

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def assemble_urls(self):
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


@lru_cache
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.assemble_urls()
    return settings