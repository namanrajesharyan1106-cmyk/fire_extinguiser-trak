import os
import re

router_dir = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers'
endpoints = []

for filename in os.listdir(router_dir):
    if filename.endswith('.py') and filename != '__init__.py':
        path = os.path.join(router_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'@router\.(get|post|put|patch|delete)\(\s*[\'\"]([^\'\"]+)[\'\"]', content)
            for match in matches:
                endpoints.append(f'[{filename[:-3].upper()}] {match[0].upper()} {match[1]}')

for e in sorted(endpoints):
    print(e)
