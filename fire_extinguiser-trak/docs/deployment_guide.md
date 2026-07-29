# Deployment Guide — Fire Safety Asset Management System

This guide outlines the procedure for deploying the backend application using Docker.

## Prerequisites
- Docker Engine & Docker Compose
- Properly configured `.env` file containing production secrets

## Step 1: Environment Configuration
1. Navigate to the `backend/` directory.
2. Copy the template: `cp .env.example .env`
3. Edit `.env` to include actual credentials:
   - Change `ENVIRONMENT` to `production`.
   - Set a strong `SECRET_KEY`.
   - Provide a highly secure `DEFAULT_ADMIN_PASSWORD` (Required on first startup).
   - Uncomment and configure `DATABASE_URL` for PostgreSQL.

## Step 2: Build & Start Containers
From the root of the repository, execute:
```bash
docker-compose build
docker-compose up -d
```
This will initialize the PostgreSQL database, automatically execute SQLAlchemy's `create_all`, seed the default Admin user, and start the FastAPI web server on port 8000.

## Step 3: Verify Health Status
Check the status of the backend by calling the health endpoint:
```bash
curl http://localhost:8000/health
```
You should see: `{"status": "healthy", "version": "3.0.0"}`

## Step 4: Reverse Proxy Configuration (Nginx)
Configure Nginx to route traffic to the backend API:
```nginx
server {
    listen 80;
    server_name api.firesafety.company.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_addrs;
        
        client_max_body_size 12M; # Support 10MB file uploads
    }
}
```
