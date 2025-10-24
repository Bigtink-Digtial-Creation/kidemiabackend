import urllib.parse
from dotenv import load_dotenv
from typing import Optional, List
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, validator

load_dotenv()


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    APP_NAME: str = "Kidemia API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    API_KEY: str = Field(..., env="API_KEY")
    API_KEY_SECONDARY: str | None = Field(..., env="API_KEY_SECONDARY")

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    DB_USER: str = Field(..., env="DB_USER")
    DB_PASS: str = Field(..., env="DB_PASS")
    DB_HOST: str = Field(..., env="DB_HOST")
    DB_PORT: int = Field(default=5432, env="DB_PORT")
    DB_NAME: str = Field(..., env="DB_NAME")

    @property
    def DATABASE_URL(self) -> str:
        safe_pass = urllib.parse.quote_plus(self.DB_PASS)
        return f"postgresql://{self.DB_USER}:{safe_pass}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    DB_ECHO: bool = False  # SQLAlchemy echo
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    CACHE_TTL: int = 300  # 5 minutes default

    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8

    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
        "https://kidemia-pro.vercel.app",
        "https://kidemia-super-admin.vercel.app",
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: Optional[str] = None

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf", "doc", "docx"]

    # AWS S3 (Optional)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None

    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    PAYSTACK_SECRET_KEY: Optional[str] = None
    PAYSTACK_PUBLIC_KEY: Optional[str] = None

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 500

    # Alternative: Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = None

    PROCTORING_ENABLED: bool = True
    PROCTORING_SCREENSHOT_INTERVAL: int = 30  # seconds
    PROCTORING_FACE_DETECTION: bool = True
    PROCTORING_TAB_SWITCHING_ALLOWED: int = 3  # max tab switches

    POINTS_PER_CORRECT_ANSWER: int = 10
    POINTS_PER_TEST_COMPLETION: int = 50
    POINTS_PER_EXAM_COMPLETION: int = 100
    STREAK_BONUS_MULTIPLIER: float = 1.5

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_ENABLED: bool = True

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND"
    )

    SENTRY_DSN: Optional[str] = None

    TESTING: bool = False
    TEST_DATABASE_URL: Optional[PostgresDsn] = None

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures we only create one instance.
    """
    return Settings()


# Create a global settings instance
settings = get_settings()
