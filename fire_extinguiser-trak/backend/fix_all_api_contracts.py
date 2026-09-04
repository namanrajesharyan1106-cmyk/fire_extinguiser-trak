import os, re
routers_dir = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers'

def inject_create_api_response(content):
    if 'def create_api_response(' not in content:
        # inject after router = APIRouter()
        injection = '\n\ndef create_api_response(\n    success: bool, message: str, data: Any = None, errors: Any = None\n) -> dict:\n    return {"success": success, "message": message, "data": data, "errors": errors}\n'
        content = content.replace('router = APIRouter()', 'router = APIRouter()' + injection)
        if 'from typing import ' not in content:
            content = 'from typing import Any\n' + content
        elif 'Any' not in content:
            content = content.replace('from typing import ', 'from typing import Any, ')
    return content


# 1. inspections.py
path = os.path.join(routers_dir, 'inspections.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = inject_create_api_response(content)
content = content.replace('@router.get("", response_model=List[schemas.InspectionResponse])', '@router.get("", response_model=schemas.APIResponse[List[schemas.InspectionResponse]])')
content = content.replace('    return inspections', '    return create_api_response(True, "Inspections retrieved", inspections)')
content = content.replace('@router.post("", response_model=schemas.InspectionResponse, status_code=201)', '@router.post("", response_model=schemas.APIResponse[schemas.InspectionResponse], status_code=201)')
content = content.replace('    return new_insp', '    return create_api_response(True, "Inspection created", new_insp)')
content = content.replace('@router.get("/{inspection_id}", response_model=schemas.InspectionResponse)', '@router.get("/{inspection_id}", response_model=schemas.APIResponse[schemas.InspectionResponse])')
content = content.replace('    return insp', '    return create_api_response(True, "Inspection retrieved", insp)')
content = content.replace('    return {"attachment_id": attachment.id, "file_path": attachment.file_path, "label": label}', '    return create_api_response(True, "Photo uploaded", {"attachment_id": attachment.id, "file_path": attachment.file_path, "label": label})')
content = content.replace('@router.get("/{inspection_id}/photos", response_model=List[schemas.AttachmentResponse])', '@router.get("/{inspection_id}/photos", response_model=schemas.APIResponse[List[schemas.AttachmentResponse]])')
content = content.replace('    return db.query(models.Attachment)', '    photos = db.query(models.Attachment).filter(models.Attachment.related_type == "inspection", models.Attachment.related_id == str(inspection_id)).all()\n    return create_api_response(True, "Photos retrieved", photos)')
# remove existing return db.query if we replaced it. Wait, the original code is:
# return (\n        db.query(models.Attachment)\n        .filter(...)\n        .all()\n    )
content = re.sub(r'return \(\s*db\.query\(models\.Attachment\).*?\.all\(\)\s*\)', r'photos = db.query(models.Attachment).filter(models.Attachment.related_type == "inspection", models.Attachment.related_id == str(inspection_id)).all()\n    return create_api_response(True, "Photos retrieved", photos)', content, flags=re.DOTALL)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)


# 2. maintenance.py
path = os.path.join(routers_dir, 'maintenance.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = inject_create_api_response(content)
content = content.replace('@router.get("", response_model=List[schemas.MaintenanceResponse])', '@router.get("", response_model=schemas.APIResponse[List[schemas.MaintenanceResponse]])')
content = re.sub(r'return \(\s*query\.order_by.*?\.all\(\)\s*\)', r'tickets = query.order_by(models.Maintenance.opened_date.desc()).offset(skip).limit(limit).all()\n    return create_api_response(True, "Maintenance tickets retrieved", tickets)', content, flags=re.DOTALL)
content = content.replace('    return {\n        "count": len(tickets),\n        "tickets": [schemas.MaintenanceResponse.model_validate(t) for t in tickets],\n    }', '    return create_api_response(True, "Open tickets retrieved", {"count": len(tickets), "tickets": [schemas.MaintenanceResponse.model_validate(t) for t in tickets]})')
content = content.replace('@router.get("/{ticket_id}", response_model=schemas.MaintenanceResponse)', '@router.get("/{ticket_id}", response_model=schemas.APIResponse[schemas.MaintenanceResponse])')
content = content.replace('    return ticket', '    return create_api_response(True, "Ticket retrieved", ticket)')
content = content.replace('@router.post("", response_model=schemas.MaintenanceResponse, status_code=201)', '@router.post("", response_model=schemas.APIResponse[schemas.MaintenanceResponse], status_code=201)')
content = content.replace('    return new_ticket', '    return create_api_response(True, "Ticket created", new_ticket)')
content = content.replace('@router.put("/{ticket_id}", response_model=schemas.MaintenanceResponse)', '@router.put("/{ticket_id}", response_model=schemas.APIResponse[schemas.MaintenanceResponse])')
content = content.replace('@router.put("/{ticket_id}/status", response_model=schemas.MaintenanceResponse)', '@router.put("/{ticket_id}/status", response_model=schemas.APIResponse[schemas.MaintenanceResponse])')
content = content.replace('@router.put("/{ticket_id}/close", response_model=schemas.MaintenanceResponse)', '@router.put("/{ticket_id}/close", response_model=schemas.APIResponse[schemas.MaintenanceResponse])')
content = content.replace('    return {\n        "attachment_id": attachment.id,\n        "file_path": attachment.file_path,\n        "label": label,\n    }', '    return create_api_response(True, "Photo uploaded", {"attachment_id": attachment.id, "file_path": attachment.file_path, "label": label})')
content = content.replace('@router.get("/{ticket_id}/photos", response_model=List[schemas.AttachmentResponse])', '@router.get("/{ticket_id}/photos", response_model=schemas.APIResponse[List[schemas.AttachmentResponse]])')
content = re.sub(r'return \(\s*db\.query\(models\.Attachment\).*?\.all\(\)\s*\)', r'photos = db.query(models.Attachment).filter(models.Attachment.related_type == "maintenance", models.Attachment.related_id == str(ticket_id)).all()\n    return create_api_response(True, "Photos retrieved", photos)', content, flags=re.DOTALL)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)


# 3. dashboard.py
path = os.path.join(routers_dir, 'dashboard.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = inject_create_api_response(content)
# we need to replace all "return {" with "return create_api_response(True, 'Success', {"
# but more safely:
for endpoint in ['/summary', '/assets-by-status', '/inspections-compliance', '/maintenance-trends', '/recent-activities', '/upcoming-amc', '/location-risks']:
    content = content.replace(f'@router.get("{endpoint}")', f'@router.get("{endpoint}", response_model=schemas.APIResponse)')
content = re.sub(r'return (\{[\s\S]*?\})\n\n', r'return create_api_response(True, "Dashboard data retrieved", \1)\n\n', content)
content = re.sub(r'return (\[[\s\S]*?\])\n\n', r'return create_api_response(True, "Dashboard data retrieved", \1)\n\n', content)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated backend routers for Phase 5")
