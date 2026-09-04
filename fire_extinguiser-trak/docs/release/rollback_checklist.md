# Production Rollback Strategy & Checklist
**Version:** v1.0 Production Go-Live
**System:** Fire Safety Asset Management System

## Overview
This document outlines the emergency rollback procedure to be executed if the production deployment fails post-migration, resulting in critical service interruption or data corruption.

## Decision Criteria for Rollback
- Application fails to start or continuously crashes on the production node.
- Migrations fail or result in database corruption.
- API requests fail universally across the platform (e.g. Authentication is completely broken).
- Performance degrades unacceptably (e.g., 90% queries timing out).

## Rollback Execution Sequence

### Phase 1: Halt Degradation
- [ ] Notify business stakeholders and IT Operations immediately: "INITIATING EMERGENCY ROLLBACK".
- [ ] Block incoming traffic at the Load Balancer to prevent partial transactions.
- [ ] Stop all FastAPI backend service instances.

### Phase 2: Database Restoration
- [ ] If migrations applied successfully but logic failed:
      - Run `alembic downgrade <previous_revision_hash>`.
- [ ] If database is corrupted or downgrades fail:
      - Drop the current database schema.
      - Restore the full encrypted backup taken during the Pre-Deployment Checklist (`pg_restore`).
- [ ] Verify database integrity (check row counts against backup manifest).

### Phase 3: Application Restoration
- [ ] Roll back the codebase to the previous stable Release Tag (or `v0.9-stable`).
- [ ] Rebuild static assets (if frontend was deployed) to match the legacy API contract.
- [ ] Deploy the reverted backend containers.
- [ ] Restart backend services.

### Phase 4: Validation & Traffic Restoration
- [ ] Execute standard Smoke Tests against the restored environment.
- [ ] Verify Login, Dashboard, and read-only endpoints.
- [ ] Re-enable incoming traffic at the Load Balancer.
- [ ] Monitor logs strictly for 30 minutes for residual anomalies.

## Post-Mortem
- Save all backend logs and database error traces.
- Conduct a blameless Post-Mortem within 24 hours to analyze the root cause of the deployment failure.
