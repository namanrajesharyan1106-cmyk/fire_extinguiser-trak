import os
models_dir = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\models'

def replace_in_file(filename, old, new):
    path = os.path.join(models_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

replace_in_file('asset.py', 'mapped_column(ForeignKey("locations.location_id"))', 'mapped_column(ForeignKey("locations.location_id"), index=True)')
replace_in_file('inspection.py', 'mapped_column(ForeignKey("assets.asset_id"))', 'mapped_column(ForeignKey("assets.asset_id"), index=True)')
replace_in_file('inspection.py', 'mapped_column(ForeignKey("locations.location_id"))', 'mapped_column(ForeignKey("locations.location_id"), index=True)')
replace_in_file('inspection.py', 'mapped_column(ForeignKey("users.id"))', 'mapped_column(ForeignKey("users.id"), index=True)')
replace_in_file('maintenance.py', 'mapped_column(ForeignKey("assets.asset_id"))', 'mapped_column(ForeignKey("assets.asset_id"), index=True)')
replace_in_file('maintenance.py', 'mapped_column(ForeignKey("locations.location_id"))', 'mapped_column(ForeignKey("locations.location_id"), index=True)')
replace_in_file('maintenance.py', 'mapped_column(ForeignKey("users.id"))', 'mapped_column(ForeignKey("users.id"), index=True)')
replace_in_file('maintenance.py', 'mapped_column(ForeignKey("inspection.inspection_id"))', 'mapped_column(ForeignKey("inspection.inspection_id"), index=True)')
replace_in_file('audit.py', 'mapped_column(ForeignKey("users.id"))', 'mapped_column(ForeignKey("users.id"), index=True)')

print("Replaced successfully")
