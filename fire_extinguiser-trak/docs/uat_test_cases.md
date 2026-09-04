# UAT Test Cases
**Date:** 2026-07-24
**Phase:** 11 - User Acceptance Testing (UAT)

## Overview
This document outlines the User Acceptance Testing scenarios for the Fire Safety Asset Management System. These scenarios validate end-to-end business workflows and system integrity under simulated production conditions.

---

### Scenario 1: Asset Lifecycle
**Objective:** Validate that a fire safety asset can be successfully provisioned, assigned to a location, and pass a routine inspection.

**Steps:**
1. Log in as an Administrator.
2. Create a new Location (`POST /api/locations`).
3. Create a new Asset (`POST /api/assets`).
4. Link the Asset to the Location (`POST /api/assets/{id}/link/{loc_id}`).
5. Submit a Passed Inspection (`POST /api/inspections`).

**Expected Result:** All endpoints return `2xx` success codes. Asset status becomes 'Active', Location holds the linked Asset, and Inspection is recorded.
**Status:** PASS

---

### Scenario 2: Defect Workflow
**Objective:** Validate that a failed inspection automatically provisions a Maintenance Ticket and correctly transitions asset status.

**Steps:**
1. Log in as an Administrator.
2. Create a new Location and Asset, and link them.
3. Submit a Failed Inspection (`POST /api/inspections`) with failed checklist items.
4. Verify auto-creation of Maintenance Ticket (`GET /api/maintenance`).
5. Close the Maintenance Ticket (`PUT /api/maintenance/{id}/close`).

**Expected Result:** Inspection failure correctly provisions a high-priority maintenance ticket. The asset is placed 'Under Maintenance'. Closing the ticket restores asset status to 'Active'.
**Status:** PASS

---

### Scenario 3: Negative / RBAC Testing
**Objective:** Validate that constraints prevent duplicate assets and that unauthenticated users are correctly rejected by protected endpoints.

**Steps:**
1. Log in as an Administrator.
2. Create a new Asset.
3. Attempt to create another Asset with the same exact Serial Number.
4. Attempt to fetch protected Dashboard Stats (`GET /api/dashboard/stats`) without an Authorization header.

**Expected Result:** The system rejects the duplicate asset creation with `400 Bad Request`. Unauthenticated requests to protected endpoints return `401 Unauthorized`.
**Status:** PASS

