"""Phase 1 & 2 - Backend and Database Validation"""
import traceback

try:
    # Phase 1: Module Load
    from app.core.database import engine, SessionLocal
    from app.models import Base
    from sqlalchemy import inspect, text

    print("=" * 60)
    print("PHASE 1 - MODULE LOAD")
    print("=" * 60)

    # Check all model imports
    from app.models import (
        AuditLog, Asset, AssetHistory, Attachment,
        Department, Inspection, Location, Maintenance,
        Notification, PasswordHistory, Permission, Plant,
        RefreshToken, Role, SystemConfig, User,
        role_permissions,
    )
    print("All models imported: OK")

    # Check all router imports
    from app.routers import (
        admin, assets, auth, dashboard, inspections,
        locations, maintenance, notifications, reports, search,
    )
    print("All routers imported: OK")

    # Check all service imports
    from app.services import (
        asset_service, audit_service, auth_service,
        dashboard_service, user_service,
    )
    print("All services imported: OK")

    # Check dependencies
    from app.core.dependencies import get_current_user, require_permission
    print("Dependencies imported: OK")

    import app.main
    print("app.main loaded: OK")
    print()

    # Phase 2: Database Validation
    print("=" * 60)
    print("PHASE 2 - DATABASE VALIDATION")
    print("=" * 60)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Total tables: {len(tables)}")
    print()

    expected_tables = [
        "users", "roles", "permissions", "role_permissions",
        "locations", "assets", "asset_history", "inspection",
        "maintenance", "notifications", "audit_logs", "attachments",
        "refresh_tokens", "password_history", "plants", "departments",
        "system_config",
    ]
    for t in sorted(expected_tables):
        if t in tables:
            cols = inspector.get_columns(t)
            pks = inspector.get_pk_constraint(t)
            fks = inspector.get_foreign_keys(t)
            idxs = inspector.get_indexes(t)
            print(f"  [OK] {t}: cols={len(cols)}, PKs={pks['constrained_columns']}, FKs={len(fks)}, Indexes={len(idxs)}")
        else:
            print(f"  [MISSING] {t}")

    # Check for data
    print()
    print("Row counts:")
    db = SessionLocal()
    try:
        for model, name in [
            (User, "users"), (Location, "locations"), (Asset, "assets"),
            (Inspection, "inspection"), (Maintenance, "maintenance"),
            (Role, "roles"), (AuditLog, "audit_logs"),
        ]:
            count = db.query(model).count()
            print(f"  {name}: {count} rows")
    finally:
        db.close()

except Exception as e:
    print(f"FAILED: {e}")
    traceback.print_exc()
