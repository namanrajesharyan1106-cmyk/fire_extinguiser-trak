import sys
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

sys.path.append(r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend')
from app.core.database import Base, engine, SessionLocal
from app import models

inspector = inspect(engine)
db_tables = inspector.get_table_names()
model_tables = Base.metadata.tables.keys()

output_file = r'c:\Users\naman\.gemini\antigravity-ide\brain\71d442ca-1e9a-4742-8db8-2866d0eac867\implementation_plan.md'

markdown = "# Phase 6: Database Integrity & Data Validation Plan\n\n"
markdown += "## User Review Required\n"
markdown += "> [!IMPORTANT]\n> This plan outlines the database schema audit, model validation, and necessary fixes to ensure full data integrity and alignment between SQLAlchemy models and the actual SQLite database.\n\n"

markdown += "## Proposed Changes\n\n"

# 1. Check for table mismatches
missing_in_db = set(model_tables) - set(db_tables)
missing_in_models = set(db_tables) - set(model_tables)

markdown += "### Schema Audits & Mismatches\n\n"
if missing_in_db:
    markdown += f"- **Tables in Models but missing in DB**: {', '.join(missing_in_db)}\n"
if missing_in_models:
    markdown += f"- **Tables in DB but missing in Models**: {', '.join(missing_in_models)} (Legacy artifacts?)\n"

if not missing_in_db and not missing_in_models:
    markdown += "- All model tables correctly match the database tables.\n\n"

markdown += "### Detailed Table Audits\n\n"

for table_name in db_tables:
    if table_name == 'alembic_version':
        continue
    
    markdown += f"#### Table: `{table_name}`\n"
    columns = inspector.get_columns(table_name)
    fks = inspector.get_foreign_keys(table_name)
    indexes = inspector.get_indexes(table_name)
    
    # We can perform advanced checks here
    # Example: Check if there's a primary key
    pk = inspector.get_pk_constraint(table_name)
    if not pk or not pk.get('constrained_columns'):
        markdown += "- **Problem**: Missing Primary Key!\n"
        markdown += f"- **Fix**: Add a primary key to `{table_name}` via Alembic.\n"
    
    # Example: Check if any columns are missing indexes that are heavily searched (like asset_id in inspections)
    for col in columns:
        col_name = col['name']
        if col_name.endswith('_id') and col_name != pk['constrained_columns'][0]:
            # It's a foreign key or reference, should ideally be indexed
            is_indexed = any(col_name in idx['column_names'] for idx in indexes)
            if not is_indexed:
                markdown += f"- **Problem**: Missing Index on Foreign Key/Reference `{col_name}`.\n"
                markdown += f"- **Fix**: Create an index for `{table_name}.{col_name}` to optimize query performance.\n"
    
    markdown += "\n"

# 2. Check for Orphan Records (Data Validation)
markdown += "### Data Validation (Orphan Records)\n\n"
db = SessionLocal()

# Check orphan inspections (missing asset or location)
orphan_inspections_asset = db.query(models.Inspection).filter(
    models.Inspection.asset_id.isnot(None),
    ~models.Inspection.asset_id.in_(db.query(models.Asset.asset_id))
).count()
if orphan_inspections_asset > 0:
    markdown += f"- **Problem**: Found {orphan_inspections_asset} Orphan Inspections pointing to non-existent Assets.\n"

# Check orphan maintenance
orphan_maintenance = db.query(models.Maintenance).filter(
    ~models.Maintenance.asset_id.in_(db.query(models.Asset.asset_id))
).count()
if orphan_maintenance > 0:
    markdown += f"- **Problem**: Found {orphan_maintenance} Orphan Maintenance tickets pointing to non-existent Assets.\n"

db.close()

markdown += "\n## Verification Plan\n"
markdown += "- Apply missing indexes via Alembic migrations.\n"
markdown += "- Clean up legacy tables if any.\n"
markdown += "- Delete or reassign orphan records.\n"
markdown += "- Perform a full CRUD regression test across all major tables directly in the database.\n"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(markdown)

print("Generated Phase 6 Implementation Plan.")
