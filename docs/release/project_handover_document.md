# Project Handover Document
**Date:** 2026-07-24
**System:** Fire Safety Asset Management System

## 1. System Overview
The Fire Safety Asset Management System is a modern, full-stack application built for industrial factory floors to track, inspect, and maintain critical fire safety infrastructure.
- **Backend:** FastAPI, Python 3.10+, SQLAlchemy, SQLite (Dev) / PostgreSQL (Prod).
- **Frontend:** React, Vite, TailwindCSS (Future integration), Axios.
- **Core Architecture:** JWT Auth, RBAC, RESTful APIs.

## 2. Technical Asset Index
| Resource | Location | Description |
| --- | --- | --- |
| **Source Code** | `/backend`, `/frontend` | Full application source repository. |
| **API Documentation** | `http://[host]/docs` | Live Swagger/OpenAPI documentation. |
| **Database Schema** | `docs/schema_ERD.md` | Full Entity Relationship definitions. |
| **Migration Scripts** | `/backend/alembic/versions` | Sequential Alembic migration files. |

## 3. Operational Runbooks
- **Backup & Restore:** Refer to `rollback_checklist.md` for encrypted backup instructions.
- **Configuration Management:** Refer to `.env.example` for the master configuration schema.
- **SSL / TLS:** Managed via NGINX terminating proxy; certificates rotated via Certbot/ACME.

## 4. Administrative Security (RBAC)
- **ADMIN:** Unrestricted read/write, user management, and configuration.
- **SAFETY HEAD:** Full read/write over assets, locations, reporting, and high-level defect closures.
- **SAFETY OFFICER:** Execution of inspections, verifying defects.
- **INSPECTOR:** Restricted to QR scanning, execution of inspections, and uploading photos.
- **MAINTENANCE:** Restricted to viewing assigned tickets, uploading evidence, and requesting verification.

## 5. End of Development Handover
The Development Team officially hands over the operation, administration, and Level 1/Level 2 support of the Fire Safety Asset Management System to the IT Operations Team, as per the Hypercare exit protocols.
