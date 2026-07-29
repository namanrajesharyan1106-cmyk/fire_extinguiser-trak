from typing import Optional

from sqlalchemy.orm import Session

from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate
from .base_repository import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_by_employee_id(self, db: Session, *, employee_id: str) -> Optional[User]:
        return db.query(User).filter(User.employee_id == employee_id).first()

    def get_active_users_by_role(self, db: Session, role: str):
        return db.query(User).filter(User.role == role, User.status == "Active").all()


user_repo = UserRepository(User)
