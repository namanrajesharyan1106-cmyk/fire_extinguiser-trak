from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# For PostgreSQL we want proper connection pooling, SQLite gets single-thread optimizations
if "sqlite" in settings.get_database_url:
    engine = create_engine(
        settings.get_database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    engine = create_engine(
        settings.get_database_url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_timeout=30,
        pool_recycle=1800, # Recycle connections after 30 minutes
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Synchronous dependency to get DB session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
