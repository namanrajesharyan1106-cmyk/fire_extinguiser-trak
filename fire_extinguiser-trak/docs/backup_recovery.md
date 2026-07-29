# Backup & Disaster Recovery Guide

## Backup Strategy

### 1. Database Backups
If using PostgreSQL (Recommended for Production), schedule `pg_dump` daily:
```bash
docker exec -t firesafety_db pg_dumpall -c -U postgres > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql
```
Store these SQL dumps in a secure, off-site location (e.g., AWS S3).

### 2. File Uploads Backup
Asset images and maintenance evidence photos are stored in `backend/uploads`. This directory must be backed up securely.
```bash
tar -czvf uploads_backup_`date +%d-%m-%Y`.tar.gz backend/uploads/
```

### 3. Configuration Backup
Always retain a secure backup of the production `.env` file, as it contains cryptographic keys (`SECRET_KEY`) used to sign JWT tokens.

## Disaster Recovery Procedure

In the event of total server loss:

1. **Provision New Infrastructure:** Install Docker and Docker Compose on a new host.
2. **Restore Codebase:** Clone the repository and place the backed-up `.env` file inside `backend/`.
3. **Restore Uploads:** Extract the uploads backup tarball into `backend/uploads`.
4. **Initialize System:** Start the application stack with `docker-compose up -d`. Let it run initialization, which will create an empty database schema.
5. **Restore Database Data:** Execute the SQL dump against the fresh PostgreSQL container:
   ```bash
   cat dump_file.sql | docker exec -i firesafety_db psql -U postgres
   ```
6. **Verify Consistency:** Run the cleanup script (`python backend/scripts/cleanup_orphaned_files.py`) to verify that the database records and physical uploaded files are fully synchronized.
