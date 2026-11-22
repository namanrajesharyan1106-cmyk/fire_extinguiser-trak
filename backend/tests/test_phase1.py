import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings, validate_production_config
from app.core.database import SessionLocal
from app.models.user import User
from app.models.auth import RefreshToken
from app.core.security import create_access_token, get_password_hash
from datetime import datetime, timedelta
import uuid

client = TestClient(app)

def test_config_validation():
    # 1. Empty SECRET_KEY
    cfg1 = Settings(ENVIRONMENT="production", SECRET_KEY="", DEFAULT_ADMIN_PASSWORD="StrongPassword123!")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        validate_production_config(cfg1)

    # 2. Short SECRET_KEY
    cfg2 = Settings(ENVIRONMENT="production", SECRET_KEY="short_key_123", DEFAULT_ADMIN_PASSWORD="StrongPassword123!")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        validate_production_config(cfg2)

    # 3. Placeholder SECRET_KEY
    cfg3 = Settings(ENVIRONMENT="production", SECRET_KEY="generate_a_secure_random_key_here", DEFAULT_ADMIN_PASSWORD="StrongPassword123!")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        validate_production_config(cfg3)

    # 4. Empty DEFAULT_ADMIN_PASSWORD
    cfg4 = Settings(ENVIRONMENT="production", SECRET_KEY="a" * 32, DEFAULT_ADMIN_PASSWORD="")
    with pytest.raises(ValueError, match="DEFAULT_ADMIN_PASSWORD"):
        validate_production_config(cfg4)

    # 5. DEFAULT_ADMIN_PASSWORD starting with "change"
    cfg5 = Settings(ENVIRONMENT="production", SECRET_KEY="a" * 32, DEFAULT_ADMIN_PASSWORD="changeme123")
    with pytest.raises(ValueError, match="DEFAULT_ADMIN_PASSWORD"):
        validate_production_config(cfg5)

    # 6. Valid production config
    cfg_valid = Settings(ENVIRONMENT="production", SECRET_KEY="a" * 32, DEFAULT_ADMIN_PASSWORD="StrongAdminPassword123!")
    validate_production_config(cfg_valid)  # Should not raise

    # 7. Development config ignores restrictions
    cfg_dev = Settings(ENVIRONMENT="development", SECRET_KEY="dev", DEFAULT_ADMIN_PASSWORD="dev")
    validate_production_config(cfg_dev)  # Should not raise


def test_login_generic_message():
    # Unknown email
    resp1 = client.post("/api/auth/login", data={"username": "nonexistent_user_999@example.com", "password": "Password123!"})
    assert resp1.status_code == 401
    detail1 = resp1.json().get("message")

    # Known email with wrong password
    resp2 = client.post("/api/auth/login", data={"username": "admin@fireext.com", "password": "WrongPassword999!"})
    assert resp2.status_code == 401
    detail2 = resp2.json().get("message")

    assert detail1 == "Invalid email or password"
    assert detail2 == "Invalid email or password"
    assert detail1 == detail2


def test_first_login_enforcement():
    db = SessionLocal()
    try:
        emp_id = f"FL_{uuid.uuid4().hex[:6]}"
        email = f"{emp_id}@example.com"
        user = User(
            employee_id=emp_id,
            name="First Login User",
            email=email,
            password_hash=get_password_hash("InitialPass123!"),
            role="INSPECTOR",
            department="Safety",
            plant="PP02",
            status="Active",
            is_first_login=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Blocked on assets endpoint
    resp_assets = client.get("/api/assets", headers=headers)
    assert resp_assets.status_code == 403
    body = resp_assets.json()
    assert body.get("code") == "PASSWORD_CHANGE_REQUIRED"

    # Allowed on /api/auth/me
    resp_me = client.get("/api/auth/me", headers=headers)
    assert resp_me.status_code == 200
    assert resp_me.json()["data"]["is_first_login"] is True

    # Allowed on /api/auth/change-password
    resp_change = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "InitialPass123!", "new_password": "UpdatedPass123!"}
    )
    assert resp_change.status_code == 200

    # After password change, is_first_login is False and access is unlocked
    resp_assets_after = client.get("/api/assets", headers=headers)
    assert resp_assets_after.status_code == 200


def test_health_scoping():
    # Public health returns only status
    resp_pub = client.get("/api/health")
    assert resp_pub.status_code == 200
    data_pub = resp_pub.json()
    assert data_pub == {"status": "healthy"}
    assert "cpu_percent" not in data_pub
    assert "memory_rss_mb" not in data_pub
    assert "version" not in data_pub

    # Diagnostics without auth -> 401
    resp_diag_unauth = client.get("/api/health/diagnostics")
    assert resp_diag_unauth.status_code == 401

    # Diagnostics with non-admin (e.g. VIEWER or INSPECTOR) -> 403
    db = SessionLocal()
    try:
        emp_id = f"V_{uuid.uuid4().hex[:6]}"
        viewer = User(
            employee_id=emp_id,
            name="Viewer User",
            email=f"{emp_id}@example.com",
            password_hash=get_password_hash("Pass123!"),
            role="VIEWER",
            department="Safety",
            plant="PP02",
            status="Active",
            is_first_login=False,
        )
        db.add(viewer)
        db.commit()
        viewer_id = viewer.id
        admin_user = db.query(User).filter(User.role == "ADMIN").first()
        admin_id = admin_user.id
    finally:
        db.close()

    viewer_token = create_access_token(data={"sub": str(viewer_id)})
    resp_diag_viewer = client.get("/api/health/diagnostics", headers={"Authorization": f"Bearer {viewer_token}"})
    assert resp_diag_viewer.status_code == 403

    # Diagnostics with admin -> 200
    admin_token = create_access_token(data={"sub": str(admin_id)})
    resp_diag_admin = client.get("/api/health/diagnostics", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_diag_admin.status_code == 200
    diag_data = resp_diag_admin.json()
    assert "database" in diag_data
    assert "system" in diag_data
    assert "version" in diag_data


def test_sessions_query():
    db = SessionLocal()
    try:
        emp_id = f"SESS_{uuid.uuid4().hex[:6]}"
        user = User(
            employee_id=emp_id,
            name="Session Test User",
            email=f"{emp_id}@example.com",
            password_hash=get_password_hash("Pass123!"),
            role="VIEWER",
            department="Safety",
            plant="PP02",
            status="Active",
            is_first_login=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 1. Valid active session
        t_active = RefreshToken(
            token_hash=get_password_hash("active_tok_1"),
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_revoked=False
        )
        # 2. Revoked session
        t_revoked = RefreshToken(
            token_hash=get_password_hash("revoked_tok_1"),
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_revoked=True
        )
        # 3. Expired session
        t_expired = RefreshToken(
            token_hash=get_password_hash("expired_tok_1"),
            user_id=user.id,
            created_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=1),
            is_revoked=False
        )
        db.add_all([t_active, t_revoked, t_expired])
        db.commit()
        db.refresh(t_active)
        active_id = t_active.id
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id)})
    resp = client.get("/api/auth/sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    sessions = resp.json().get("data", [])
    # Should only return the 1 active session
    assert len(sessions) == 1
    assert sessions[0]["id"] == active_id

