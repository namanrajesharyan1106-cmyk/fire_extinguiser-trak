import os
import sys
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

    # Security (No default for SECRET_KEY in production)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/firesafety.db")

    # Optional Postgres DB parameters
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: str = os.getenv("DB_PORT", "")
    DB_NAME: str = os.getenv("DB_NAME", "")

    # File uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp"}
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", 10))

    # Default Admin
    DEFAULT_ADMIN_EMAIL: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@fireext.com")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "")
    DEFAULT_ADMIN_EMPLOYEE_ID: str = os.getenv("DEFAULT_ADMIN_EMPLOYEE_ID", "EMP001")
    DEFAULT_ADMIN_NAME: str = os.getenv("DEFAULT_ADMIN_NAME", "System Administrator")
    DEFAULT_ADMIN_DEPARTMENT: str = os.getenv("DEFAULT_ADMIN_DEPARTMENT", "Safety")
    DEFAULT_ADMIN_ROLE: str = os.getenv("DEFAULT_ADMIN_ROLE", "ADMIN")
    DEFAULT_ADMIN_PLANT: str = os.getenv("DEFAULT_ADMIN_PLANT", "Head Office")

    # Login Security
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    # Password Policy
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_DIGIT: bool = True
    REQUIRE_SPECIAL_CHAR: bool = True
    PASSWORD_HISTORY_LIMIT: int = 3

    # Application
    APP_TITLE: str = os.getenv("APP_TITLE", "FireSafety Pro — QR Asset Management (Enterprise v3)")
    APP_VERSION: str = os.getenv("APP_VERSION", "3.0.0")

    # Notification thresholds
    EXPIRY_ALERT_DAYS: int = 30
    REFILL_ALERT_DAYS: int = 15
    AMC_ALERT_DAYS: int = 30
    INSPECTION_OVERDUE_DAYS: int = 3

    # CORS
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")

    @property
    def get_database_url(self) -> str:
        if self.DB_USER and self.DB_PASSWORD and self.DB_HOST and self.DB_NAME:
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT or 5432}/{self.DB_NAME}"
        return self.DATABASE_URL

    @property
    def allowed_origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()

if settings.ENVIRONMENT == "production":
    if settings.SECRET_KEY == False:
        print("[CRITICAL] SECRET_KEY is not set in production. Refusing to start.")
        sys.exit(1)
    if settings.DEFAULT_ADMIN_PASSWORD == False:
        print("[CRITICAL] DEFAULT_ADMIN_PASSWORD is not set in production. Refusing to start.")
        sys.exit(1)
