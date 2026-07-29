import os
import sys

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import auth, models
from app.core.database import Base, SessionLocal, engine

# Create all tables
Base.metadata.create_all(bind=engine)


def seed():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = (
            db.query(models.User)
            .filter(models.User.email == "admin@example.com")
            .first()
        )
        if not admin:
            print("Creating default admin user...")
            admin_user = models.User(
                employee_id="ADM001",
                name="System Administrator",
                email="admin@example.com",
                password_hash=auth.get_password_hash("admin123"),
                department="IT",
                role="Admin",
                status="Active",
            )
            db.add(admin_user)
            db.commit()
            print("Admin user created successfully.")
        else:
            print("Admin user already exists.")

    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
