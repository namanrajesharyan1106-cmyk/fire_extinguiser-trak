import os
import sys
from sqlalchemy import create_engine, MetaData, Table, inspect, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.system import MasterPlant, MasterDepartment, SequenceTracker
from app.core.database import Base

def run_migration():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'firesafety.db'))
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Create new tables
    Base.metadata.create_all(bind=engine, tables=[
        MasterPlant.__table__,
        MasterDepartment.__table__,
        SequenceTracker.__table__
    ])
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "plants" in existing_tables:
        print("Migrating plants...")
        with engine.connect() as conn:
            plants_res = conn.execute(text("SELECT plant_name, status FROM plants")).fetchall()
            for row in plants_res:
                name = row[0]
                status = row[1]
                if name:
                    is_active = (status == "Active")
                    # Check if already exists
                    existing = session.query(MasterPlant).filter_by(name=name).first()
                    if not existing:
                        session.add(MasterPlant(name=name, is_active=is_active))
        session.commit()
        print("Plants migrated.")
        
    if "departments" in existing_tables:
        print("Migrating departments...")
        with engine.connect() as conn:
            dept_res = conn.execute(text("SELECT dept_name, status FROM departments")).fetchall()
            for row in dept_res:
                name = row[0]
                status = row[1]
                if name:
                    is_active = (status == "Active")
                    existing = session.query(MasterDepartment).filter_by(name=name).first()
                    if not existing:
                        session.add(MasterDepartment(name=name, is_active=is_active))
        session.commit()
        print("Departments migrated.")
        
    # We can drop the tables manually
    with engine.connect() as conn:
        if "plants" in existing_tables:
            conn.execute(text("DROP TABLE plants"))
        if "departments" in existing_tables:
            conn.execute(text("DROP TABLE departments"))
        conn.commit()
        print("Old tables dropped.")
        
    session.close()
    print("Migration complete.")

if __name__ == "__main__":
    run_migration()
