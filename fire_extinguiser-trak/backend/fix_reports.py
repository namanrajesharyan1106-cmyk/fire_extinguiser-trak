import sys

path = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers\reports.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from ..core import dependencies as auth', 'from ..core import dependencies as auth\nfrom .auth import create_api_response')
content = content.replace('return {"count": len(result), "data": result}', 'return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
