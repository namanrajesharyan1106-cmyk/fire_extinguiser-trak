import os
import re

router_dir = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers'
output_file = r'c:\Users\naman\.gemini\antigravity-ide\brain\71d442ca-1e9a-4742-8db8-2866d0eac867\implementation_plan.md'

markdown = "# Phase 7: Authentication & Authorization Hardening Plan\n\n"
markdown += "## User Review Required\n"
markdown += "> [!IMPORTANT]\n> This plan outlines the security audit for Authentication, Authorization (RBAC), and Session Management. The audit found hardcoded secrets, weak password policies, and missing endpoint protections.\n\n"

markdown += "## Proposed Changes\n\n"

markdown += "### 1. JWT Security & Secrets Configuration\n"
markdown += "- **Vulnerability**: `SECRET_KEY` is currently hardcoded in `backend/app/core/config.py` as `\"fire-safety-super-secret-key-change-in-production-2024\"`.\n"
markdown += "- **Fix**: Load `SECRET_KEY` from an environment variable (e.g. `.env`) and throw a startup error if it falls back to a default in production.\n"
markdown += "- **Vulnerability**: Token expiration handling needs strict validation to ensure refresh tokens are rotated and blacklisted on logout.\n"
markdown += "\n"

markdown += "### 2. Password Security Policy\n"
markdown += "- **Vulnerability**: Missing strict password complexity requirements in User creation and Password Reset routes.\n"
markdown += "- **Fix**: Implement a regex validator for passwords (min 8 chars, 1 uppercase, 1 number, 1 special character) inside the Pydantic schemas (`UserCreate`, `UserUpdate`, `ResetPassword`).\n"
markdown += "\n"

markdown += "### 3. Role-Based Access Control (RBAC) Hardening\n"

markdown += "#### Discovered Endpoint Permissions Matrix:\n"

unprotected_routes = []

for filename in sorted(os.listdir(router_dir)):
    if not filename.endswith('.py') or filename == '__init__.py':
        continue
    
    module_name = filename[:-3].upper()
    path = os.path.join(router_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all route definitions
    matches = re.finditer(r'@router\.(get|post|put|patch|delete)\(\s*[\'\"]([^\'\"]+)[\'\"][^)]*\)\s*def\s+\w+\((.*?)\):', content, re.DOTALL)
    
    has_routes = False
    for match in matches:
        if not has_routes:
            has_routes = True
        
        method = match.group(1).upper()
        route = match.group(2)
        params = match.group(3)
        
        # Check if auth.require_permission is in params
        perm_match = re.search(r'Depends\([^)]*require_permission\([\'\"]([^\'\"]+)[\'\"]\)', params)
        if perm_match:
            perm = perm_match.group(1)
        else:
            # Check for get_current_user (authenticated but not specific permission)
            if 'get_current_user' in params or 'get_current_active_user' in params:
                perm = "Authenticated User (Any Role)"
            else:
                perm = "UNPROTECTED"
                unprotected_routes.append(f"{method} {filename[:-3]}:{route}")
    
if unprotected_routes:
    markdown += "\n> [!CAUTION]\n> The following routes appear to lack explicit `Depends` on authentication decorators:\n"
    for r in unprotected_routes:
        markdown += f"- `{r}`\n"
    markdown += "\n- **Fix**: Apply `Depends(auth.get_current_user)` or `auth.require_permission(...)` to these routes.\n\n"

markdown += "### 4. Account Security & Session Management\n"
markdown += "- **Fix**: Ensure that `POST /logout` explicitly blacklists the active JWT token (e.g. Redis blocklist or DB token table).\n"
markdown += "- **Fix**: Implement concurrent session limits by tracking active refresh tokens per user in the DB.\n"
markdown += "\n"

markdown += "### 5. Security Regression Tests\n"
markdown += "- Test expired JWT rejection.\n"
markdown += "- Test role escalation attempts (e.g. Technician trying to hit `/admin` endpoints).\n"
markdown += "- Verify that unauthenticated requests correctly yield HTTP 401 and unauthorized yield HTTP 403.\n"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(markdown)

print("Generated Phase 7 Implementation Plan.")
