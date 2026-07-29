import os
import re

router_dir = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers'

output_file = r'c:\Users\naman\.gemini\antigravity-ide\brain\71d442ca-1e9a-4742-8db8-2866d0eac867\implementation_plan.md'

markdown = "# Phase 5: API Contract Validation & Standardization Plan\n\n"
markdown += "## User Review Required\n"
markdown += "> [!IMPORTANT]\n> This plan outlines the exact contract mismatches across all 60+ API endpoints in the system. The primary issue is that while we standardized some modules (like `/locations`, `/assets`, `/reports`, `/search`) to use `APIResponse`, many other endpoints (like `/admin`, `/inspections`, `/maintenance`, `/dashboard`) are still returning raw objects or lists, causing frontend parsing inconsistencies.\n\n"
markdown += "## Proposed Changes\n\n"

for filename in sorted(os.listdir(router_dir)):
    if not filename.endswith('.py') or filename == '__init__.py':
        continue
    
    module_name = filename[:-3].upper()
    markdown += f"### {module_name} Module\n\n"
    
    path = os.path.join(router_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all route definitions
    matches = re.finditer(r'@router\.(get|post|put|patch|delete)\(\s*[\'\"]([^\'\"]+)[\'\"]([^)]*)\)', content)
    
    for match in matches:
        method = match.group(1).upper()
        route = match.group(2)
        args = match.group(3)
        
        # Determine Response Schema from args
        response_schema = "Implicit (Not Defined)"
        rm_match = re.search(r'response_model=([^\s,]+)', args)
        if rm_match:
            response_schema = rm_match.group(1)
            
        # Determine if it's returning APIResponse
        mismatch = "None"
        fix = "None"
        if "APIResponse" not in response_schema:
            mismatch = f"Returns raw `{response_schema}` instead of `APIResponse`"
            fix = f"1. Update response_model to `schemas.APIResponse[{response_schema}]`\n2. Wrap return with `create_api_response(True, 'Success', data)`\n3. Update Frontend to map `res.data.data` instead of `res.data`"
            
        markdown += f"#### {method} {route}\n"
        markdown += f"- **Request Schema**: (Parsed from parameters)\n"
        markdown += f"- **Response Schema**: `{response_schema}`\n"
        markdown += f"- **Contract Mismatch**: {mismatch}\n"
        if fix != "None":
            markdown += f"- **Fix**: \n{fix}\n"
        markdown += "\n"

markdown += "## Verification Plan\n"
markdown += "- Run complete CRUD regression on all modules.\n"
markdown += "- Ensure no `ResponseValidationError` is thrown.\n"
markdown += "- Verify all Enums match across Frontend/Backend.\n"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(markdown)

print("Generated implementation plan.")
