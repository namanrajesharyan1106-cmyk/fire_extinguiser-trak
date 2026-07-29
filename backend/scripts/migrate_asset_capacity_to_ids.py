import os
import sys
from sqlalchemy import text
from app.core.database import SessionLocal
from app import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    db = SessionLocal()
    try:
        logger.info("Starting Master Data Migration...")
        
        # 1. Fetch unique string values
        asset_types = set()
        capacities = set()
        
        # From assets
        for r in db.execute(text("SELECT DISTINCT asset_type FROM assets WHERE asset_type IS NOT NULL")).fetchall():
            if r[0]: asset_types.add(r[0].strip())
        for r in db.execute(text("SELECT DISTINCT capacity FROM assets WHERE capacity IS NOT NULL")).fetchall():
            if r[0]: capacities.add(r[0].strip())
            
        # From locations
        for r in db.execute(text("SELECT DISTINCT required_asset_type FROM locations WHERE required_asset_type IS NOT NULL")).fetchall():
            if r[0]: asset_types.add(r[0].strip())
        for r in db.execute(text("SELECT DISTINCT required_capacity FROM locations WHERE required_capacity IS NOT NULL")).fetchall():
            if r[0]: capacities.add(r[0].strip())
            
        logger.info(f"Found {len(asset_types)} unique asset types, {len(capacities)} unique capacities in transactional tables.")

        # 2. Insert missing masters
        for name in asset_types:
            existing = db.query(models.MasterAssetType).filter(models.MasterAssetType.name.ilike(name)).first()
            if not existing:
                logger.info(f"Adding new Master Asset Type: {name}")
                db.add(models.MasterAssetType(name=name, is_active=True))
        
        for name in capacities:
            existing = db.query(models.MasterCapacityType).filter(models.MasterCapacityType.name.ilike(name)).first()
            if not existing:
                logger.info(f"Adding new Master Capacity Type: {name}")
                db.add(models.MasterCapacityType(name=name, is_active=True))
                
        db.commit()
        
        # Re-fetch masters as a case-insensitive map
        asset_master_map = {m.name.lower(): m.id for m in db.query(models.MasterAssetType).all()}
        capacity_master_map = {m.name.lower(): m.id for m in db.query(models.MasterCapacityType).all()}
        
        # 3. Alter tables
        # SQLite: Add columns if they don't exist
        try:
            db.execute(text("ALTER TABLE assets ADD COLUMN asset_type_id INTEGER REFERENCES master_asset_types(id)"))
        except Exception as e:
            logger.info("assets.asset_type_id might already exist: " + str(e))
            
        try:
            db.execute(text("ALTER TABLE assets ADD COLUMN capacity_id INTEGER REFERENCES master_capacity_types(id)"))
        except Exception as e:
            logger.info("assets.capacity_id might already exist: " + str(e))
            
        try:
            db.execute(text("ALTER TABLE locations ADD COLUMN required_asset_type_id INTEGER REFERENCES master_asset_types(id)"))
        except Exception as e:
            logger.info("locations.required_asset_type_id might already exist: " + str(e))
            
        try:
            db.execute(text("ALTER TABLE locations ADD COLUMN required_capacity_id INTEGER REFERENCES master_capacity_types(id)"))
        except Exception as e:
            logger.info("locations.required_capacity_id might already exist: " + str(e))
            
        db.commit()
        
        # 4. Update data in assets
        assets = db.execute(text("SELECT asset_id, asset_type, capacity FROM assets")).fetchall()
        for a_id, a_type, cap in assets:
            type_id = asset_master_map.get(a_type.strip().lower()) if a_type else None
            cap_id = capacity_master_map.get(cap.strip().lower()) if cap else None
            if type_id or cap_id:
                db.execute(
                    text("UPDATE assets SET asset_type_id = :tid, capacity_id = :cid WHERE asset_id = :aid"),
                    {"tid": type_id, "cid": cap_id, "aid": a_id}
                )
                
        # 5. Update data in locations
        locations = db.execute(text("SELECT location_id, required_asset_type, required_capacity FROM locations")).fetchall()
        for l_id, a_type, cap in locations:
            type_id = asset_master_map.get(a_type.strip().lower()) if a_type else None
            cap_id = capacity_master_map.get(cap.strip().lower()) if cap else None
            if type_id or cap_id:
                db.execute(
                    text("UPDATE locations SET required_asset_type_id = :tid, required_capacity_id = :cid WHERE location_id = :lid"),
                    {"tid": type_id, "cid": cap_id, "lid": l_id}
                )
                
        db.commit()
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
