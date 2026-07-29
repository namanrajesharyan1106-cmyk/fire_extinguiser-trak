# Pre-Deployment & Production Go-Live Checklist
**Version:** v1.0 Production Go-Live
**System:** Fire Safety Asset Management System

## 1. Environment Readiness (Pre-Flight)
- [ ] Codebase frozen (Release Tag v1.0.0 created).
- [ ] Production build verified (frontend `npm run build` succeeds).
- [ ] Environment variables verified against `.env.production`.
- [ ] Secret Keys rotated (JWT Secret, Admin Initial Password).
- [ ] SSL Certificates verified valid for all production domains.
- [ ] DNS propagation confirmed for production endpoints.
- [ ] Storage volume attached and writable for `uploads/photos/` and `uploads/qrcodes/`.

## 2. Database Preparation
- [ ] Full backup of the previous staging/production DB state taken and encrypted.
- [ ] PostgreSQL connection pooling configured in `app/core/database.py`.
- [ ] Alembic initialized.
- [ ] Executed `alembic upgrade head`.
- [ ] Verified Migration History is completely linear.
- [ ] Verified Indexes (`ix_maintenance_maintenance_id`, `ix_users_email`, etc.) are established.
- [ ] Pre-flight data-seeding executed (e.g. Roles/Permissions inserted via `create_default_admin`).

## 3. Deployment Execution (Zero Downtime / Maintenance Window)
- [ ] Disable incoming traffic at WAF / Load Balancer.
- [ ] Deploy backend API containers (FastAPI, Python 3.10+).
- [ ] Deploy static frontend assets (React/Vite build) to CDN / NGINX.
- [ ] Restart application services (Backend via Gunicorn with Uvicorn workers).
- [ ] Re-enable incoming traffic.

## 4. Post-Deployment Immediate Checks
- [ ] Backend API Healthcheck (`GET /api/health`) returns 200 OK.
- [ ] Frontend loads without console errors.
- [ ] Centralized Logging emitting structured logs.
- [ ] Prometheus/Grafana or equivalent monitoring telemetry active.
- [ ] CORS policies restrict origins to production domains.
