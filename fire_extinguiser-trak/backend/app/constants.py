"""
Application-wide constants: roles, permissions, enums, and the permission matrix.
"""

# ─── Roles ────────────────────────────────────────────────────────────────────
ROLES = [
    "ADMIN",
    "SAFETY HEAD",
    "SAFETY OFFICER",
    "INSPECTOR",
    "MAINTENANCE",
    "VIEWER",
    "IT ADMIN",
]

# ─── Asset Types ──────────────────────────────────────────────────────────────
ASSET_TYPES = [
    "ABC",
    "CO2",
    "Foam",
    "Water",
    "DCP",
    "Clean Agent",
    "Hydrant",
    "Hydrant Hose",
    "Hose Reel",
    "Hydrant Valve",
    "Wet Chemical",
]

# ─── Asset Status ─────────────────────────────────────────────────────────────
ASSET_STATUSES = [
    "Active",
    "Expired",
    "Under Maintenance",
    "Condemned",
    "In Transit",
    "Decommissioned",
]

# ─── Location Status ──────────────────────────────────────────────────────────
LOCATION_STATUSES = ["Active", "Inactive", "Under Renovation"]

# ─── Risk Categories ──────────────────────────────────────────────────────────
RISK_CATEGORIES = ["Low", "Medium", "High", "Critical"]

# ─── Inspection Status ────────────────────────────────────────────────────────
INSPECTION_STATUSES = ["Pass", "Fail", "Conditional Pass"]
CHECKLIST_VALUES = ["Pass", "Fail", "NA"]

# Mandatory checklist fields — if any FAIL, overall = FAIL
MANDATORY_CHECKLIST_FIELDS = ["pressure", "seal", "pin", "gauge"]
ALL_CHECKLIST_FIELDS = [
    "pressure",
    "seal",
    "pin",
    "gauge",
    "hose",
    "nozzle",
    "visibility",
    "accessibility",
    "mounting",
    "safety_tag",
    "cylinder_damage",
]

# ─── Maintenance Status ───────────────────────────────────────────────────────
MAINTENANCE_STATUSES = [
    "Open",
    "Assigned",
    "Accepted",
    "In Progress",
    "Waiting Spare",
    "Completed",
    "Verified",
    "Closed",
]

# Valid status transitions
MAINTENANCE_TRANSITIONS = {
    "Open": ["Assigned", "Closed"],
    "Assigned": ["Accepted", "Open"],
    "Accepted": ["In Progress"],
    "In Progress": ["Waiting Spare", "Completed"],
    "Waiting Spare": ["In Progress", "Completed"],
    "Completed": ["Verified"],
    "Verified": ["Closed"],
    "Closed": [],
}

MAINTENANCE_PRIORITIES = ["Low", "Medium", "High", "Critical"]

# ─── Movement Types ───────────────────────────────────────────────────────────
MOVEMENT_TYPES = [
    "Assigned",
    "Replacement",
    "Transfer",
    "Repair",
    "Temporary",
    "Emergency",
    "Decommission",
]

# ─── Notification Types ───────────────────────────────────────────────────────
NOTIFICATION_TYPES = [
    "INSPECTION_FAILED",
    "ASSET_EXPIRED",
    "REFILL_DUE",
    "AMC_DUE",
    "MAINTENANCE_PENDING",
    "INSPECTION_OVERDUE",
    "ASSET_ASSIGNED",
    "USER_CREATED",
    "SYSTEM",
]

# ─── Attachment Labels ────────────────────────────────────────────────────────
ATTACHMENT_LABELS = [
    "Before",
    "After",
    "Inspection Evidence",
    "Damage Evidence",
    "Maintenance Evidence",
    "Other",
]

ATTACHMENT_RELATED_TYPES = ["inspection", "maintenance", "asset", "location"]

# ─── Permission Matrix ────────────────────────────────────────────────────────
# Format: permission_key -> list of roles that have it
PERMISSIONS = {
    # Dashboard
    "view_dashboard": [
        "ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
        "IT ADMIN",
    ],
    # Locations
    "view_locations": [
        "ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
    ],
    "create_location": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    "edit_location": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    "delete_location": ["ADMIN", "SAFETY HEAD"],
    "generate_qr": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    # Assets
    "view_assets": [
        "ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
    ],
    "create_asset": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    "edit_asset": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    "delete_asset": ["ADMIN", "SAFETY HEAD"],
    "assign_asset": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    # Inspections
    "view_inspections": [
        "ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
    ],
    "create_inspection": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER", "INSPECTOR"],
    "delete_inspection": ["ADMIN", "SAFETY HEAD"],
    # Maintenance
    "view_maintenance": [
        "ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
    ],
    "create_maintenance": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER", "INSPECTOR"],
    "edit_maintenance": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER", "MAINTENANCE"],
    "verify_maintenance": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    "close_maintenance": ["ADMIN", "SAFETY HEAD"],
    # Reports
    "view_reports": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER", "VIEWER"],
    "export_reports": ["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
    # Users
    "view_users": ["ADMIN", "IT ADMIN"],
    "create_user": ["ADMIN", "IT ADMIN"],
    "edit_user": ["ADMIN", "IT ADMIN"],
    "delete_user": ["ADMIN"],
    "reset_password": ["ADMIN", "IT ADMIN"],
    # Admin
    "manage_plants": ["ADMIN"],
    "manage_departments": ["ADMIN", "IT ADMIN"],
    "manage_system_config": ["ADMIN", "IT ADMIN"],
    "view_audit_logs": ["ADMIN", "IT ADMIN"],
    "manage_asset_types": ["ADMIN"],
    # Notifications
    "view_notifications": [
        "ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
        "IT ADMIN",
    ],
    # Search
    "global_search": [
        "ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
        "IT ADMIN",
    ],
}


def role_has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    allowed_roles = PERMISSIONS.get(permission, [])
    return role in allowed_roles
