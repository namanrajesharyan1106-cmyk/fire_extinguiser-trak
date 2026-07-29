# UAT Defect Log
**Date:** 2026-07-24
**Phase:** 11 - User Acceptance Testing (UAT)

## Overview
This document logs the runtime defects identified during automated UAT execution and their corresponding fixes to ensure production stability.

---

### Defect 1: NameError on Inspection Creation
- **ID:** DEF-001
- **Module:** `backend/app/routers/inspections.py`
- **Description:** A `NameError` was raised (`new_insp` is not defined) when returning the API response after successfully creating an inspection.
- **Root Cause:** A typo in the return statement referenced an undefined variable `new_insp` instead of the instantiated `new_inspection`.
- **Resolution:** Updated the return statement to reference `new_inspection` correctly.
- **Status:** FIXED / VERIFIED

### Defect 2: TypeError on Maintenance Ticket Auto-Creation
- **ID:** DEF-002
- **Module:** `backend/app/services/inspection_service.py`
- **Description:** When an inspection failed, the backend returned a `500 Internal Server Error` with `TypeError: 'source' is an invalid keyword argument for Maintenance`.
- **Root Cause:** The system attempted to pass a `source` argument to the SQLAlchemy `Maintenance` model, but `source` is not a defined column.
- **Resolution:** Removed the invalid `source` argument from the model initialization inside `process_inspection`.
- **Status:** FIXED / VERIFIED

### Defect 3: ResponseValidationError on Maintenance Ticket Auto-Creation
- **ID:** DEF-003
- **Module:** `backend/app/services/inspection_service.py`
- **Description:** When fetching auto-created maintenance tickets, the `GET /api/maintenance` endpoint threw a `ResponseValidationError` because `opened_date` was null.
- **Root Cause:** The `opened_date` was configured as a required field in `MaintenanceResponse`, but the `inspection_service` neglected to set it when auto-generating the ticket upon a failed inspection.
- **Resolution:** Added `opened_date=datetime.utcnow()` to the `Maintenance` ticket constructor in `inspection_service.py`.
- **Status:** FIXED / VERIFIED

### Defect 4: IntegrityError during UAT Re-Execution
- **ID:** DEF-004
- **Module:** `backend/scripts/run_uat_scenarios.py`
- **Description:** Running the UAT suite multiple times resulted in a `400 Bad Request` regarding Database Integrity (`uq_location_name_plant`).
- **Root Cause:** Static location names ("UAT Test Room") caused unique constraint violations on subsequent test runs in the SQLite database.
- **Resolution:** Implemented dynamic suffixing using Unix timestamps for generated location names and IDs in the UAT script.
- **Status:** FIXED / VERIFIED
