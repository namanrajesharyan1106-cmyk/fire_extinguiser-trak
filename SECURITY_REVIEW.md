# FireSafety Pro — Enterprise Security Hardening & Authorization Review

**Application:** FireSafety Pro (QR-Based Fire Safety Asset Management System)  
**Date:** November 2026  
**Target Environment:** FastAPI (Python 3.14 / SQLite & PostgreSQL ready) + React / Vite (TypeScript + Material-UI)  
**Branch:** `security-hardening`  
**Review Status:** Completed & Fully Verified  

---

## 1. Executive Summary

A comprehensive multi-phase security, access-control, and code-quality audit and remediation was performed on FireSafety Pro. The objective was to eliminate critical vulnerabilities including unauthenticated static file exposure, privilege escalation, cross-tenant data leakage, brute-force vulnerabilities, credential enumeration, workflow spoofing, and insecure dependencies, while strictly preserving business logic and existing API response envelopes (`{success, message, data, errors}`).

All fixes have been validated with automated test suites (**76 unit and regression tests passing**), zero Ruff linter warnings, zero TypeScript/oxlint errors, and successful production asset compilation.

---

## 2. Hardening Phases & Remediations

### Phase 0: Repository & Dependency Hygiene
- **Pinned Dependencies:** Generated a clean `backend/requirements.txt` with pinned versions based on actual imports (FastAPI, SQLAlchemy, Alembic, Pydantic-Settings, python-jose, bcrypt, slowapi, python-multipart, openpyxl, pillow, pytest, httpx).
- **Sensitive Artifact Exclusion:** Configured `.gitignore` to reject `.env`, `*.db`, `*.db.bak`, `uploads/`, `.ruff_cache/`, `__pycache__/`, and zip archives. Created sanitized `.env.example` templates for both backend and frontend.
- **Removed Dead Artifacts:** Deleted legacy root scratch scripts (`backend/*.py`, `fix_*.py`), sample zip files (`schemas.zip`, `uploads.zip`, `scripts.zip`), and test QR images.
- **Deduplicated Modules:** Eliminated redundant root modules (`app/config.py`, `app/database.py`, `app/auth.py`, `app/logger.py`, `app/constants.py`) and unified on `backend/app/core/*` as the single source of truth.
- **Lifespan Migration & Production Docs:** Replaced deprecated `@app.on_event("startup")` handlers with modern FastAPI `lifespan` context manager. Disabled `/docs`, `/redoc`, and `/openapi.json` automatically when `ENVIRONMENT == "production"`.
- **Frontend Encoding:** Fixed `frontend/.env` encoding from UTF-16 to UTF-8 with standard `VITE_API_URL` configuration.
- **Workflow Bugfix:** Removed duplicate asset status reset blocks in `maintenance.py:update_ticket_status`.

---

### Phase 1: Authentication & Configuration Hardening
- **Production Secret Validation:** Configured `Settings` to reject default placeholders (e.g., `secret`, `change_me`, keys < 32 characters) in production environments.
- **Brute-Force Protection & Account Lockout:** Integrated `slowapi` rate limiting (10 attempts/minute on `/api/auth/login`) combined with database-backed failed attempt tracking. Accounts are temporarily locked for 15 minutes after 5 consecutive failed attempts.
- **Generic Error Messaging:** Unified login error responses to `"Invalid email or password"` across missing users, invalid passwords, and inactive accounts, completely eliminating account enumeration.
- **Password Complexity Policy:** Enforced strong password rules: minimum 8 characters, at least 1 uppercase letter, 1 lowercase letter, 1 numeric digit, and 1 special character.
- **First-Login Enforcement:** Flagged newly created accounts with `is_first_login = True`. Middleware and route dependencies enforce password reset before access to any core resource is granted.
- **Token Security & Revocation:** 
  - Short-lived Access Tokens (default 30 minutes) + Refresh Tokens (default 7 days).
  - Explicit session tracking in `RefreshToken` table with IP and User-Agent capture.
  - Provided `GET /api/auth/sessions` and `DELETE /api/auth/sessions/{id}` for self-service session management and remote revocation.
  - Automatic token revocation on password change and role demotion.
- **Protected Diagnostics:** Moved system diagnostic metrics (`/health/diagnostics`) behind authentication and the `view_system_health` permission.

---

### Phase 2: Multi-Tenant Data Scoping (Plants & Departments)
- **Centralized Scope Engine:** Implemented `get_user_scope(user, db)` and `apply_scope(query, user, db, model)` in `backend/app/core/scope.py`:
  - `ADMIN`: Global scope (unrestricted access across all plants and departments).
  - `SAFETY HEAD`: Plant-scoped across all departments within assigned plants.
  - `SAFETY OFFICER`, `INSPECTOR`, `MAINTENANCE`, `VIEWER`: Strictly scoped to assigned plants and specific assigned department.
- **Fail-Closed Default:** Non-admin users without assigned plants receive an empty scope (`Scope(plants=set())`), causing all queries to return empty results rather than leaking cross-plant data.
- **Cross-Plant QR & Direct Lookup Isolation:** `check_record_scope` verifies record ownership on single-entity retrievals (`/assets/{id}`, `/locations/{id}`, `/inspections/{id}`, `/maintenance/{id}`). Scanning an asset or location from another plant returns a standard 404 (Not Found) to prevent resource existence disclosure.
- **Query Parameter Validation:** Added `validate_plant_param` to reject unauthorized plant filter tampering with `403 Forbidden`.

---

### Phase 3: Role Hierarchy & User Management Access Controls
- **Role Ranks Hierarchy:** Enforced rank hierarchy:
  - `ADMIN` (100) > `IT ADMIN` (80) > `SAFETY HEAD` (60) > `SAFETY OFFICER` (50) > `INSPECTOR` (30) = `MAINTENANCE` (30) > `VIEWER` (10).
- **Privilege Escalation Prevention:** Users cannot create, update, or assign roles equal to or higher than their own rank. `IT ADMIN` cannot create or modify `ADMIN` users.
- **Self-Modification Prevention:** Users cannot modify their own role or toggle their own active status.
- **Last-Admin Safeguard:** Database checks guarantee that the last active `ADMIN` account cannot be deleted, deactivated, or demoted.
- **Plant Scope Delegation:** Users can only assign plants to subordinate users that are within their own assigned plants.

---

### Phase 4: Maintenance Workflow & Inspection Integrity
- **State Machine Enforcement:** Validated state transitions in `MAINTENANCE_TRANSITIONS`:
  - `Reported` -> `Assigned` -> `In Progress` -> `Pending Parts` / `Resolved` -> `Verified` -> `Closed`.
  - Disallowed arbitrary status skips or regression from closed states.
- **Ticket Ownership:** Technicians can only view and update tickets assigned to them or unassigned tickets within their plant scope.
- **Tamper-Proof Verification:** In `PUT /api/maintenance/{ticket_id}/status`, `ticket.verified_by` is bound server-side to `current_user.name` when transitioning to `Verified` or `Closed`. Client-supplied spoofed values are ignored.
- **Technician Re-assignment Restrictions:** Only `ADMIN`, `IT ADMIN`, and `SAFETY HEAD` can reassign tickets to other technicians.

---

### Phase 5: Secure File Storage & Serving
- **Eliminated Static Directory Exposure:** Removed `app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")`. Public access to the filesystem is completely disabled.
- **Authenticated File Endpoint:** Created `GET /api/files/{category}/{filename}` protected by `get_current_user` and scoped permission verification (`view_inspections`, `view_maintenance`).
- **Path Traversal Protection:** Validated filenames using `os.path.basename` and resolved paths against canonical upload directories, aborting with 400 on traversal attempts (`..`, absolute paths).
- **Magic-Byte MIME Validation:** Verified file signatures using magic bytes rather than trusting `Content-Type` headers or file extensions.
- **Pillow Image Sanitization:** Validated images via `PIL.Image`, stripped EXIF metadata and potential polyglot script payloads, and re-encoded image streams before saving to disk.
- **Upload Size Limits:** Enforced 5 MB maximum file upload limit across all endpoints.

---

### Phase 6: Frontend Authorization & Token Lifecycle
- **Axios Refresh Interceptor:** Configured automatic `401 Unauthorized` interception in `frontend/src/api/axios.ts`. Queues failed requests, acquires a new access token via `POST /api/auth/refresh`, and transparently replays queued requests without user disruption. Exhausted refreshes gracefully clear storage and redirect to `/login`.
- **Plant Scoping Dropdown:** Added a plant selector in `Header.tsx` populated strictly with the plants allowed for the logged-in user. Automatically appends `selectedPlant` to API requests.
- **Route Guarding:** Implemented `<RequirePermission permission="...">` in `App.tsx` and created a dedicated `/forbidden` (403 Access Denied) page.
- **First-Login Modal/Redirect:** Directs users with `is_first_login = True` immediately to `/change-password` with interactive password complexity feedback.
- **Navigation Scoping:** Replaced hardcoded `role === 'ADMIN'` checks in `Sidebar.tsx` with dynamic `hasPermission(permission)` checks.
- **ExcelJS Migration:** Replaced the legacy `xlsx` library in `Reports.tsx` with modern, vulnerability-free `exceljs`.

---

### Phase 7: Verification & Authorization Matrix
- **Automated Test Matrix:** Authored `backend/tests/test_matrix.py` testing the complete role-by-role authorization matrix against 2 plants, 7 distinct user roles, and all critical system endpoints.
- **Regression Suite:** Ran 76 backend automated tests covering bulk upload, inspections, maintenance ownership, session revocation, and scoping. **100% passing**.
- **Static Code Quality:** Verified code quality using Ruff (0 errors) and Pyright strict type resolution. Frontend passes TypeScript compilation (`tsc -b`) and `oxlint` with 0 errors.

---

## 3. Comprehensive Endpoint Authorization Matrix

| Endpoint | Method | Required Permission | Allowed Roles | Data Scoping |
| :--- | :---: | :--- | :--- | :--- |
| `/api/auth/login` | POST | None (Public) | All (Rate limited) | N/A |
| `/api/auth/refresh` | POST | None (Public) | All | Validates refresh token in DB |
| `/api/auth/logout` | POST | Authenticated | All | Current session |
| `/api/auth/sessions` | GET / DEL | Authenticated | All | Current user's sessions |
| `/api/auth/change-password`| POST | Authenticated | All | Current user |
| `/api/auth/users` | GET | `view_users` | ADMIN, IT ADMIN, SAFETY HEAD | Plant/Dept scoped |
| `/api/auth/users` | POST | `create_user` | ADMIN, IT ADMIN | Role rank < caller rank; Plant scoped |
| `/api/auth/users/{id}` | PUT | `edit_user` | ADMIN, IT ADMIN | Role rank < caller rank; Not self |
| `/api/auth/users/{id}/reset-password` | POST | `edit_user` | ADMIN, IT ADMIN | Target role rank < caller rank |
| `/api/assets` | GET | `view_assets` | All authenticated roles | Plant/Dept scoped |
| `/api/assets` | POST | `create_asset` | ADMIN, SAFETY HEAD, SAFETY OFFICER | Validates plant scope of location |
| `/api/assets/{id}` | GET | `view_assets` | All authenticated roles | 404 if outside plant scope |
| `/api/assets/{id}/link/{loc}` | POST | `edit_asset` | ADMIN, SAFETY HEAD, SAFETY OFFICER | Validates compatibility & plant scope |
| `/api/locations` | GET | `view_locations` | All authenticated roles | Plant/Dept scoped |
| `/api/locations` | POST | `create_location` | ADMIN, SAFETY HEAD, SAFETY OFFICER | Validates plant scope |
| `/api/inspections` | GET | `view_inspections` | All authenticated roles | Plant/Dept scoped |
| `/api/inspections` | POST | `create_inspection` | ADMIN, SAFETY HEAD, OFFICER, INSPECTOR | Must belong to assigned plant/dept |
| `/api/maintenance` | GET | `view_maintenance` | All authenticated roles | Technicians see assigned only; others scoped |
| `/api/maintenance` | POST | `create_maintenance`| All authenticated roles | Plant scoped |
| `/api/maintenance/{id}/status` | PUT | `update_maintenance`| Technicians (assigned only), Heads, Admins | Server-enforced `verified_by` |
| `/api/files/{cat}/{file}` | GET | `view_inspections` / `view_maintenance` | Authenticated | Scoped file streaming; no static mount |
| `/health` | GET | None (Public) | All | Basic status: `{status: "ok"}` |
| `/health/diagnostics` | GET | `view_system_health`| ADMIN, IT ADMIN | Authenticated diagnostics |

---

## 4. Key Architectural Decisions & Trade-Offs

1. **Storage of Tokens:**
   - Access and refresh tokens are managed in frontend memory and persisted in `localStorage` for PWA offline capabilities. Refresh tokens are tracked server-side in SQLite/PostgreSQL with automatic revocation on role modifications or manual logout.
   - *Trade-off:* While HTTP-only cookies offer defense against XSS, token-based authorization headers simplify PWA offline scanning and multi-platform mobile deployments.
2. **Pillow Re-encoding for File Uploads:**
   - Uploaded inspection and maintenance photos are opened with Pillow, stripped of EXIF data, re-encoded as JPEG/PNG, and saved to disk.
   - *Security Gain:* Defeats polyglot files (e.g., PHP/HTML concealed in image headers) and prevents metadata geolocation leaks.
3. **Fail-Closed Data Scoping:**
   - Rather than allowing unscoped users to view all records, any non-admin account without an assigned plant receives a `false()` filter returning zero records.
   - *Security Gain:* Guarantees multi-tenant isolation even in cases of misconfigured user onboarding.
4. **ExcelJS Migration:**
   - Fully replaced the `xlsx` package with `exceljs` across the frontend application.
   - *Security Gain:* Eliminates known prototype pollution and ReDoS vulnerabilities present in unmaintained `xlsx` releases.

---

## 5. Production Deployment Recommendations

1. **Database Migration to PostgreSQL:**
   - SQLite is currently used for development and testing. For multi-node production deployment, configure `DATABASE_URL=postgresql://user:pass@host:5432/firesafety` to support high concurrency, connection pooling, and row-level locking.
2. **Distributed Rate Limiting with Redis:**
   - Replace in-memory `slowapi` storage with Redis (`REDIS_URL`) so that login brute-force thresholds and token revocations are shared across all backend workers.
3. **Automated Backups:**
   - Configure hourly WAL (Write-Ahead Logging) archiving and daily encrypted database backups stored in an isolated, immutable object store (e.g., AWS S3 with Object Lock or Google Cloud Storage).
4. **HTTPS & Security Headers:**
   - Ensure reverse proxies (Nginx/Traefik) enforce TLS 1.3, HSTS (`Strict-Transport-Security`), and inject security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`).
