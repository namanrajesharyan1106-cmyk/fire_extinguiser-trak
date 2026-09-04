"""
Authentication router — login, refresh, logout, sessions, change-password, reset-password, user management.
"""

from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import database
from ..core import dependencies as auth
from ..core import security
from ..services import audit_service, auth_service, user_service

router = APIRouter()


def create_api_response(
    success: bool, message: str, data: Any = None, errors: Any = None
) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}


from ..core.limiter import limiter

@router.post("/login", response_model=schemas.LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    ip_address = request.client.host if request.client else None
    device_name = request.headers.get("user-agent", "Unknown Device")

    if not user:
        # Prevent timing attacks by hashing something anyway
        security.get_password_hash(form_data.password)
        audit_service.log_audit_action(
            db, "LOGIN_FAILED", 0, status="Unknown Email", request=request
        )
        raise HTTPException(status_code=401, detail="No account was found with this email address.")

    try:
        user_service.check_account_status(user)
    except HTTPException as e:
        audit_service.log_audit_action(
            db, "LOGIN_FAILED", user.id, status="Blocked", request=request
        )
        raise e

    if not security.verify_password(form_data.password, user.password_hash):
        user_service.handle_failed_login(db, user)
        audit_service.log_audit_action(
            db, "LOGIN_FAILED", user.id, status="Invalid Password", request=request
        )
        raise HTTPException(status_code=401, detail="The password you entered is incorrect.")

    if security.needs_update(user.password_hash):
        user.password_hash = security.get_password_hash(form_data.password)
        db.commit()

    user_service.handle_successful_login(db, user, ip_address, device_name)

    access_token = security.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth_service.create_refresh_token(db, user.id, request)

    audit_service.log_audit_action(db, "LOGIN", user.id, request=request)

    token_data = schemas.Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user,
    )

    response = create_api_response(True, "Login successful", token_data)
    # Hybrid response: Preserves frontend API structure but places access_token
    # at the root for Swagger UI OAuth2 compatibility
    response["access_token"] = access_token
    response["token_type"] = "bearer"
    return response


@router.post("/refresh", response_model=schemas.APIResponse[schemas.Token])
def refresh_token(
    request: Request,
    payload: schemas.TokenRefresh,
    db: Session = Depends(database.get_db),
):
    db_token = auth_service.verify_refresh_token(db, payload.refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(models.User).filter(models.User.id == db_token.user_id).first()
    if not user or user.status != "Active":
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotate token
    auth_service.revoke_refresh_token(db, db_token.id)
    new_access = security.create_access_token(data={"sub": str(user.id)})
    new_refresh = auth_service.create_refresh_token(db, user.id, request)

    token_data = schemas.Token(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        user=user,
    )
    return create_api_response(True, "Token refreshed successfully", token_data)


@router.post("/logout")
def logout(
    request: Request,
    payload: schemas.TokenRefresh,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_token = auth_service.verify_refresh_token(db, payload.refresh_token)
    if db_token and db_token.user_id == current_user.id:
        auth_service.revoke_refresh_token(db, db_token.id)

    audit_service.log_audit_action(db, "LOGOUT", current_user.id, request=request)
    return create_api_response(True, "Logged out successfully")


@router.post("/logout-all")
def logout_all(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    auth_service.revoke_all_user_tokens(db, current_user.id)
    audit_service.log_audit_action(db, "LOGOUT_ALL", current_user.id, request=request)
    return create_api_response(True, "Logged out of all devices successfully")


@router.get(
    "/sessions", response_model=schemas.APIResponse[List[schemas.SessionResponse]]
)
def get_active_sessions(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    sessions = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.user_id == current_user.id,
            models.RefreshToken == False.is_revoked,
        )
        .all()
    )
    return create_api_response(True, "Active sessions retrieved", sessions)


@router.delete("/sessions/{session_id}", response_model=schemas.APIResponse)
def terminate_session(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    session = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.id == session_id)
        .first()
    )
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    auth_service.revoke_refresh_token(db, session.id)
    return create_api_response(True, "Session terminated successfully")


@router.get("/me", response_model=schemas.APIResponse[schemas.UserResponse])
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return create_api_response(True, "Current user retrieved", current_user)


@router.post("/change-password", response_model=schemas.APIResponse)
def change_password(
    request: Request,
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not security.verify_password(
        payload.current_password, current_user.password_hash
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    try:
        user_service.change_user_password(db, current_user, payload.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    audit_service.log_audit_action(
        db, "PASSWORD_CHANGE", current_user.id, request=request
    )
    return create_api_response(True, "Password changed successfully")


@router.get("/roles", response_model=schemas.APIResponse)
def get_roles(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    roles = db.query(models.Role).all()
    role_names = [r.name for r in roles]
    return create_api_response(True, "Roles retrieved", {"roles": role_names})


# ─── User Management (ADMIN / IT ADMIN) ──────────────────────────────────────
@router.get("/users", response_model=schemas.APIResponse[List[schemas.UserResponse]])
def list_users(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_users")),
):
    users = db.query(models.User).order_by(models.User.name).all()
    return create_api_response(True, "Users retrieved", users)


@router.post(
    "/users", response_model=schemas.APIResponse[schemas.UserResponse], status_code=201
)
def create_user(
    request: Request,
    user_data: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_user")),
):
    existing = (
        db.query(models.User)
        .filter(
            (models.User.email == user_data.email)
            | (models.User.employee_id == user_data.employee_id)
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Email or Employee ID already registered"
        )

    valid_role = (
        db.query(models.Role).filter(models.Role.name == user_data.role).first()
    )
    if not valid_role:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    try:
        user_service.validate_password_policy(user_data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    new_user = models.User(
        employee_id=user_data.employee_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=security.get_password_hash(user_data.password),
        department=user_data.department,
        role=user_data.role,
        status=user_data.status or "Active",
        plant=user_data.plant,
        is_first_login=True,
        created_at=datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit_service.log_audit_action(
        db, "CREATE_USER", current_user.id, "users", str(new_user.id), request=request
    )
    return create_api_response(True, "User created successfully", new_user)


@router.get(
    "/users/{user_id}", response_model=schemas.APIResponse[schemas.UserResponse]
)
def get_user(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_users")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return create_api_response(True, "User retrieved", user)


@router.put(
    "/users/{user_id}", response_model=schemas.APIResponse[schemas.UserResponse]
)
def update_user(
    request: Request,
    user_id: int,
    user_data: schemas.UserUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("edit_user")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.role:
        valid_role = (
            db.query(models.Role).filter(models.Role.name == user_data.role).first()
        )
        if not valid_role:
            raise HTTPException(status_code=400, detail="Invalid role specified")

    for key, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    if user.status == "Active":
        user.locked_until = None
        user.failed_login_attempts = 0

    db.commit()
    db.refresh(user)

    audit_service.log_audit_action(
        db, "UPDATE_USER", current_user.id, "users", str(user_id), request=request
    )
    return create_api_response(True, "User updated successfully", user)


@router.delete("/users/{user_id}", response_model=schemas.APIResponse)
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("delete_user")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Cannot deactivate your own account"
        )

    user.status = "Inactive"
    auth_service.revoke_all_user_tokens(db, user.id)
    db.commit()

    audit_service.log_audit_action(
        db, "DEACTIVATE_USER", current_user.id, "users", str(user_id), request=request
    )
    return create_api_response(True, f"User '{user.name}' deactivated successfully")


@router.post("/users/{user_id}/reset-password", response_model=schemas.APIResponse)
def reset_user_password(
    request: Request,
    user_id: int,
    payload: schemas.ResetPasswordRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("reset_password")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user_service.change_user_password(db, user, payload.new_password)
        user.is_first_login = True  # Force password change on next login
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Revoke all tokens for the user so they are forced out and must login with new password
    auth_service.revoke_all_user_tokens(db, user.id)

    audit_service.log_audit_action(
        db,
        "ADMIN_RESET_PASSWORD",
        current_user.id,
        "users",
        str(user_id),
        request=request,
    )
    return create_api_response(
        True,
        f"Password reset for user '{user.name}'. They must change it on next login.",
    )
