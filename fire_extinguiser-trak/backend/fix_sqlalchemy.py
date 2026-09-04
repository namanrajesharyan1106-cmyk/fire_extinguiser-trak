import os
import re

app_dir = r"c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app"

for root, _, files in os.walk(app_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Fix `not Model.field` in filters
            # A bit tricky to regex, let's look for `not [a-zA-Z0-9_]+\.[a-zA-Z0-9_]+`
            # and replace with `[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.is_(False)`
            def replace_not(match):
                return f"{match.group(1)}.is_(False)"
            content = re.sub(r"not\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)", replace_not, content)
            
            # Fix `is not None`
            def replace_is_not_none(match):
                return f"{match.group(1)}.is_not(None)"
            content = re.sub(r"([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+is\s+not\s+None", replace_is_not_none, content)
            
            # Fix `is None`
            def replace_is_none(match):
                return f"{match.group(1)}.is_(None)"
            content = re.sub(r"([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+is\s+None", replace_is_none, content)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
print("done")
