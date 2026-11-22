from app.services.rbac_service import create_default_admin
from app.core.database import Base, SessionLocal, engine
from app.models import Permission, Role, User

def test_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_admin(db)
        admin = db.query(User).filter(User.email == "admin@fireext.com").first()
        assert admin is not None
        assert admin.role == "ADMIN"
        roles = db.query(Role).all()
        assert len(roles) > 0
        perms = db.query(Permission).all()
        assert len(perms) > 0
    finally:
        db.close()
