import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import get_password_hash, verify_password
from ..models.auth import PasswordHistory
from ..models.user import User
from ..repositories.user_repository import user_repo


def get_user_by_id_or_email(db: Session, identifier: str) -> Optional[User]:
    try:
        user_id = int(identifier)
        user = user_repo.get(db, user_id)
        if user:
            return user
    except ValueError:
        pass
    return user_repo.get_by_email(db, email=identifier)


def validate_password_policy(password: str) -> bool:
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long."
        )
    if settings.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if settings.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if settings.REQUIRE_DIGIT and not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if settings.REQUIRE_SPECIAL_CHAR and not re.search(
        r"[!@#$%^&*(),.?\":{}|<>]", password
    ):
        raise ValueError("Password must contain at least one special character.")
    return True


def handle_failed_login(db: Session, user: User) -> None:
    """Increment failed login attempts and lock account if threshold reached."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    user.last_failed_login = datetime.utcnow()

    if (user.failed_login_attempts or 0) >= settings.MAX_LOGIN_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(
            minutes=settings.LOCKOUT_DURATION_MINUTES
        )

    db.commit()


def handle_successful_login(
    db: Session, user: User, ip_address: Optional[str], device_name: Optional[str]
) -> None:
    """Reset failed attempts and update login tracking fields."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    user.last_login_ip = ip_address
    user.last_login_device = device_name
    db.commit()


def check_account_status(user: User) -> None:
    """Check if account is active and not locked."""
    if user.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the administrator.",
        )

    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been temporarily locked due to multiple failed login attempts.",
        )


def change_user_password(db: Session, user: User, new_password: str) -> None:
    validate_password_policy(new_password)

    # Check password history
    if settings.PASSWORD_HISTORY_LIMIT > 0:
        history = (
            db.query(PasswordHistory)
            .filter(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.created_at.desc())
            .limit(settings.PASSWORD_HISTORY_LIMIT)
            .all()
        )
        for record in history:
            if record.password_hash and verify_password(new_password, record.password_hash):
                raise ValueError(
                    "New password cannot be the same as any of the recent passwords."
                )

    new_hash = get_password_hash(new_password)
    user.password_hash = new_hash
    user.is_first_login = False

    # Add to history
    if settings.PASSWORD_HISTORY_LIMIT > 0:
        history_record = PasswordHistory(user_id=user.id, password_hash=new_hash)
        db.add(history_record)

    db.commit()
