import os, re
pages_dir = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\frontend\src\pages'

files_to_patch = ['Inspections.tsx', 'Maintenance.tsx', 'Dashboard.tsx']

for file in files_to_patch:
    path = os.path.join(pages_dir, file)
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Safely replace `return res.data` inside queryFn with `return res.data?.data || res.data`
    content = re.sub(r'return res\.data;', r'return res.data?.data || res.data;', content)
    content = re.sub(r'const [a-zA-Z0-9_]+ = res\.data;', lambda m: m.group(0).replace('res.data', '(res.data?.data || res.data)'), content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Updated frontend React Query data unwrapping")
