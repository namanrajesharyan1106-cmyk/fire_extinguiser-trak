from app.auth import create_default_admin
from app.core.database import Base, SessionLocal, engine
from app.models import Permission, Role, User

print("Starting verification...")

# Ensure tables are created
Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    print("Calling create_default_admin...")
    create_default_admin(db)

    admin = db.query(User).filter(User.email == "admin@fireext.com").first()
    print(f"Admin found: {admin.name}, Role: {admin.role}")

    roles = db.query(Role).all()
    print(f"Roles seeded: {len(roles)}")

    perms = db.query(Permission).all()
    print(f"Permissions seeded: {len(perms)}")

    print("Verification successful!")
except Exception:
    import traceback

    traceback.print_exc()
finally:
    db.close()
