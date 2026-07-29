from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import Request
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from ..models import AuditLog


def log_audit_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    old_values: Optional[str] = None,
    new_values: Optional[str] = None,
    status: str = "Success",
    request: Optional[Request] = None,
):
    ip_address = None
    device = None
    browser = None

    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        # Very basic parsing, could be expanded
        device = user_agent[:50]
        browser = user_agent[:50]

    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        device=device,
        browser=browser,
        status=status,
    )

    db.add(audit_entry)
    db.commit()
