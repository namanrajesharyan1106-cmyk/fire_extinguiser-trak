import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
import bcrypt

from .config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt(rounds=12)
    ).decode('utf-8')

def needs_update(hashed_password: str) -> bool:
    # If the hash is not a bcrypt hash or uses < 12 rounds, it needs update
    return not hashed_password.startswith("$2b$12$")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_raw_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def encode_refresh_token(user_id: int, db_token_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(db_token_id),
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodes a token and returns the payload. Raises JWTError if invalid."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
