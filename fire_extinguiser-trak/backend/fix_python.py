import os

app_dir = r"c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app"

for root, _, files in os.walk(app_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            content = content.replace(".is_not(None)", " is not None")
            content = content.replace(".is_(None)", " is None")
            content = content.replace(".is_(False)", " == False")
            content = content.replace(".is_(True)", " == True")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
print("Restored")
