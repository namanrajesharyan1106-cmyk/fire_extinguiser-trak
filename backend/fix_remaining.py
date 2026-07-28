import glob
import os
import re

app_dir = r"c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app"

for root, _, files in os.walk(app_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Fix == False to .is_(False)
            content = re.sub(r"==\s*False", ".is_(False)", content)
            content = re.sub(r"==\s*True", ".is_(True)", content)
            
            # Fix .isnot to .is_not
            content = content.replace(".isnot", ".is_not")
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
print("done")
