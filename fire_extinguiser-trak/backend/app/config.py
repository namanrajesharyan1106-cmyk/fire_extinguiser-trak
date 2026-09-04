from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Security
    SECRET_KEY: str = "fire-safety-super-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/firesafety.db"

    # File uploads
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp"}
    MAX_UPLOAD_SIZE_MB: int = 10

    # Default Admin
    DEFAULT_ADMIN_EMAIL: str = "admin@fireext.com"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_EMPLOYEE_ID: str = "EMP001"
    DEFAULT_ADMIN_NAME: str = "System Administrator"
    DEFAULT_ADMIN_DEPARTMENT: str = "Safety"
    DEFAULT_ADMIN_ROLE: str = "ADMIN"
    DEFAULT_ADMIN_PLANT: str = "Head Office"

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
    APP_TITLE: str = "FireSafety Pro — QR Asset Management"
    APP_VERSION: str = "2.0.0"

    # Notification thresholds
    EXPIRY_ALERT_DAYS: int = 30
    REFILL_ALERT_DAYS: int = 15
    AMC_ALERT_DAYS: int = 30
    INSPECTION_OVERDUE_DAYS: int = 3

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
