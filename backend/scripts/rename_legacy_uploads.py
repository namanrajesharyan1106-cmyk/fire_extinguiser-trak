"""
One-off migration script:
Renames legacy predictable upload filenames (asset_*, qr_*, maint_*, insp_*)
to random UUID filenames, and updates database records in assets, locations, and attachments.
"""

import os
import sys
import uuid

# Ensure backend root is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import SessionLocal
from app import models


def rename_legacy_files():
    db = SessionLocal()
    try:
        renamed_count = 0

        for kind in ["photos", "qr"]:
            dir_path = os.path.join(settings.UPLOAD_DIR, kind)
            if not os.path.exists(dir_path):
                continue

            for fname in os.listdir(dir_path):
                old_file_path = os.path.join(dir_path, fname)
                if not os.path.isfile(old_file_path):
                    continue

                # Check if it has a legacy prefix pattern
                if any(fname.startswith(p) for p in ["asset_", "qr_", "maint_", "insp_"]):
                    ext = os.path.splitext(fname)[1].lower()
                    new_fname = f"{uuid.uuid4().hex}{ext}"
                    new_file_path = os.path.join(dir_path, new_fname)

                    os.rename(old_file_path, new_file_path)
                    print(f"Renamed {fname} -> {new_fname}")

                    # Update DB references
                    # 1. Assets
                    assets = db.query(models.Asset).filter(models.Asset.photo.like(f"%{fname}")).all()
                    for a in assets:
                        a.photo = a.photo.replace(fname, new_fname)

                    # 2. Locations
                    locs = db.query(models.Location).filter(models.Location.qr_image_path.like(f"%{fname}")).all()
                    for l in locs:
                        l.qr_image_path = l.qr_image_path.replace(fname, new_fname)

                    # 3. Attachments
                    attaches = db.query(models.Attachment).filter(models.Attachment.file_path.like(f"%{fname}")).all()
                    for att in attaches:
                        att.file_path = att.file_path.replace(fname, new_fname)

                    renamed_count += 1

        db.commit()
        print(f"Migration completed: Renamed {renamed_count} files and updated DB paths.")
    except Exception as e:
        db.rollback()
        print(f"Error during file migration: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    rename_legacy_files()
