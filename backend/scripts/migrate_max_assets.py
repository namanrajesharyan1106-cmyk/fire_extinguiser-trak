import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.config import settings

def run_migration():
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE locations ADD COLUMN max_assets INTEGER DEFAULT 15"))
            print("Successfully added max_assets to locations table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column max_assets already exists.")
            else:
                raise e

if __name__ == "__main__":
    run_migration()
