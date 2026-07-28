import os
import sys
from sqlalchemy.orm import Session
from pathlib import Path

# Add the parent directory to sys.path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.core.config import settings
from app import models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def main():
    db: Session = next(get_db())
    print("Starting orphaned file cleanup...")
    
    # Get all active file paths from the database
    asset_photos = set(row[0] for row in db.query(models.Asset.photo).filter(models.Asset.photo.isnot(None)).all())
    attachment_files = set(row[0] for row in db.query(models.Attachment.file_path).filter(models.Attachment.file_path.isnot(None)).all())
    
    # Merge active references
    active_references = asset_photos.union(attachment_files)
    
    # Resolve to absolute paths (assuming they are stored as 'uploads/photos/filename.jpg')
    active_paths = set()
    for ref in active_references:
        # If ref is relative like 'uploads/photos/abc.jpg'
        # The physical path is settings.UPLOAD_DIR + '/photos/abc.jpg'
        filename = os.path.basename(ref)
        active_paths.add(filename)
        
    photos_dir = os.path.join(settings.UPLOAD_DIR, "photos")
    if not os.path.exists(photos_dir):
        print("Uploads directory does not exist. Nothing to clean.")
        return

    orphaned_count = 0
    bytes_freed = 0

    for filename in os.listdir(photos_dir):
        filepath = os.path.join(photos_dir, filename)
        if os.path.isfile(filepath):
            if filename not in active_paths:
                print(f"Removing orphaned file: {filename}")
                bytes_freed += os.path.getsize(filepath)
                os.remove(filepath)
                orphaned_count += 1
                
    print(f"Cleanup complete. Removed {orphaned_count} orphaned files. Freed {bytes_freed / (1024*1024):.2f} MB.")

if __name__ == "__main__":
    main()
