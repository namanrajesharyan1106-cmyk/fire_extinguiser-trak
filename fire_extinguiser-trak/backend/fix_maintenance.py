import os

maintenance_router = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers\maintenance.py'

with open(maintenance_router, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: create_maintenance_ticket
create_logic = '''
    ticket_data = ticket.model_dump()
    ticket_data.pop("source", None)

    new_ticket = models.Maintenance(
        **ticket_data,
        status="Open",
        opened_date=datetime.utcnow(),
    )
    db.add(new_ticket)
    
    if ticket.asset_id:
        asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
        if asset:
            asset.status = "Under Maintenance"
'''

content = content.replace('''    ticket_data = ticket.model_dump()
    ticket_data.pop("source", None)

    new_ticket = models.Maintenance(
        **ticket_data,
        status="Open",
        opened_date=datetime.utcnow(),
    )
    db.add(new_ticket)''', create_logic)


# Fix 2: update_ticket_status
status_logic = '''    if status_update.new_status == "Completed":
        ticket.completion_date = datetime.utcnow()
    elif status_update.new_status == "Closed":
        ticket.closed_date = datetime.utcnow()

    if status_update.new_status in ["Completed", "Closed", "Verified"] and ticket.asset_id:
        other_open = db.query(models.Maintenance).filter(
            models.Maintenance.asset_id == ticket.asset_id,
            models.Maintenance.maintenance_id != ticket.maintenance_id,
            models.Maintenance.status.notin_(["Closed", "Verified", "Completed"])
        ).first()
        if not other_open:
            asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
            if asset:
                asset.status = "Active"
'''

content = content.replace('''    if status_update.new_status == "Completed":
        ticket.completion_date = datetime.utcnow()
    elif status_update.new_status == "Closed":
        ticket.closed_date = datetime.utcnow()''', status_logic)


# Fix 3: close_maintenance_ticket
close_logic = '''    ticket.status = "Closed"
    ticket.closed_date = datetime.utcnow()
    ticket.remarks = remarks
    ticket.updated_at = datetime.utcnow()
    
    if ticket.asset_id:
        other_open = db.query(models.Maintenance).filter(
            models.Maintenance.asset_id == ticket.asset_id,
            models.Maintenance.maintenance_id != ticket.maintenance_id,
            models.Maintenance.status.notin_(["Closed", "Verified", "Completed"])
        ).first()
        if not other_open:
            asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
            if asset:
                asset.status = "Active"
'''

content = content.replace('''    ticket.status = "Closed"
    ticket.closed_date = datetime.utcnow()
    ticket.remarks = remarks
    ticket.updated_at = datetime.utcnow()''', close_logic)


with open(maintenance_router, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated maintenance.py logic")
