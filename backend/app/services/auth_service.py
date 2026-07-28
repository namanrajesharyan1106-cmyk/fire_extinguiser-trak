from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import decode_token, encode_refresh_token, get_password_hash, generate_raw_refresh_token

from ..models.auth import RefreshToken


def create_refresh_token(db: Session, user_id: int, request: Optional[Request] = None) -> str:
    raw_token = generate_raw_refresh_token()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    ip_address = None
    device_name = None
    if request and request.client:
        ip_address = request.client.host
    if request:
        device_name = request.headers.get("user-agent", "Unknown Device")

    db_token = RefreshToken(
        token_hash=get_password_hash(raw_token),
        user_id=user_id,
        expires_at=expire,
        ip_address=ip_address,
        device_name=device_name,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)

    encoded_jwt = encode_refresh_token(user_id, db_token.id)
    return encoded_jwt


def verify_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        token_type = payload.get("type")
        jti_str = payload.get("jti")

        if user_id is None or token_type != "refresh" or not jti_str:
            return None

        try:
            jti = int(jti_str)
        except ValueError:
            return None

        db_token = db.query(RefreshToken).filter(RefreshToken.id == jti).first()
        if not db_token:
            return None

        if db_token.is_revoked or not db_token.expires_at or db_token.expires_at < datetime.utcnow():
            return None

        return db_token
    except Exception:
        return None


def revoke_refresh_token(db: Session, token_id: int):
    db_token = db.query(RefreshToken).filter(RefreshToken.id == token_id).first()
    if db_token and not db_token.is_revoked:
        db_token.is_revoked = True
        db_token.revoked_at = datetime.utcnow()
        db.commit()


def revoke_all_user_tokens(db: Session, user_id: int):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False)
    ).update({"is_revoked": True, "revoked_at": datetime.utcnow()})
    db.commit()
