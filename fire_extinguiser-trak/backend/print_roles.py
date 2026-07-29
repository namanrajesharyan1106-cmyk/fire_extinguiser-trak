import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.gen2 import Roles

def print_roles():
    db = SessionLocal()
    roles = db.query(Roles).all()
    print([r.name for r in roles])
    db.close()

if __name__ == "__main__":
    print_roles()
