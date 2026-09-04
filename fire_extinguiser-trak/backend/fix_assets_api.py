import os, re
path = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers\assets.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix get_asset
content = content.replace('@router.get("/{asset_id}", response_model=schemas.AssetResponse)', '@router.get("/{asset_id}", response_model=schemas.APIResponse[schemas.AssetResponse])')
content = content.replace('    return asset\n', '    return create_api_response(True, "Asset retrieved", asset)\n')

# Fix create_asset
content = content.replace('@router.post("", response_model=schemas.AssetResponse, status_code=201)', '@router.post("", response_model=schemas.APIResponse[schemas.AssetResponse], status_code=201)')
content = content.replace('    return new_asset\n', '    return create_api_response(True, "Asset created", new_asset)\n')

# Fix update_asset
content = content.replace('@router.put("/{asset_id}", response_model=schemas.AssetResponse)', '@router.put("/{asset_id}", response_model=schemas.APIResponse[schemas.AssetResponse])')
content = content.replace('    return db_asset\n', '    return create_api_response(True, "Asset updated", db_asset)\n')

# Fix delete_asset
content = content.replace('return {"message": f"Asset \'{asset_id}\' deleted successfully"}', 'return create_api_response(True, f"Asset \'{asset_id}\' deleted successfully")')

# Fix link_asset_to_location
content = content.replace('    return {**result, "warnings": warnings}\n', '    return create_api_response(True, "Asset assigned", {**result, "warnings": warnings})\n')

# Fix unlink_asset
content = content.replace('    return result\n', '    return create_api_response(True, "Asset unlinked", result)\n')

# Fix get_asset_history
content = content.replace('@router.get("/{asset_id}/history", response_model=List[schemas.AssetHistoryResponse])', '@router.get("/{asset_id}/history", response_model=schemas.APIResponse[List[schemas.AssetHistoryResponse]])')
content = content.replace('    return (\n        db.query(models.AssetHistory)', '    history = (\n        db.query(models.AssetHistory)')
content = content.replace('        .offset(skip)\n        .limit(limit)\n        .all()\n    )', '        .offset(skip)\n        .limit(limit)\n        .all()\n    )\n    return create_api_response(True, "History retrieved", history)')

# Fix upload_asset_photo
content = content.replace('    return {"photo_url": asset.photo, "message": "Photo uploaded successfully"}\n', '    return create_api_response(True, "Photo uploaded successfully", {"photo_url": asset.photo})\n')


with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed assets.py API contracts")
