import re

content = open("app/models/gen2.py", "r", encoding="utf-8").read()
header = "from typing import Optional\nimport datetime\nfrom sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Table, Text, UniqueConstraint\nfrom sqlalchemy.orm import Mapped, mapped_column, relationship\nfrom ..core.database import Base\n\n"

files = {
    "asset.py": ["Assets", "AssetHistory"],
    "audit.py": ["AuditLogs", "Notifications", "Attachments"],
    "auth.py": ["RefreshTokens", "PasswordHistory"],
    "inspection.py": ["Inspection"],
    "location.py": ["Locations"],
    "maintenance.py": ["Maintenance"],
    "role.py": ["Roles", "Permissions", "t_role_permissions"],
    "system.py": ["Plants", "Departments", "SystemConfig"],
    "user.py": ["Users"],
}

for fname, classes in files.items():
    out = header
    for cls in classes:
        if cls.startswith("t_"):
            m = re.search(
                r"(^" + cls + r"\s*=\s*Table\(.*?\n\))",
                content,
                re.MULTILINE | re.DOTALL,
            )
            if m:
                out += m.group(1) + "\n\n"
        else:
            m = re.search(
                r"(^class " + cls + r"\(Base\):.*?(?=^class |^t_|\Z))",
                content,
                re.MULTILINE | re.DOTALL,
            )
            if m:
                out += m.group(1) + "\n"

    # replace plurals with singulars for class names
    out = re.sub(
        r"'(Users|Locations|Assets|Roles|Permissions|Plants|Departments|RefreshTokens|PasswordHistory|AuditLogs|Notifications|Attachments)'",
        lambda x: "'" + x.group(1)[:-1] + "'",
        out,
    )
    out = re.sub(
        r"class (Users|Locations|Assets|Roles|Permissions|Plants|Departments|RefreshTokens|PasswordHistory|AuditLogs|Notifications|Attachments)\(Base\):",
        lambda x: "class " + x.group(1)[:-1] + "(Base):",
        out,
    )

    # some classes don't end in 's'
    out = re.sub(r"'PasswordHistory'", "'PasswordHistory'", out)  # No op

    with open(f"app/models/{fname}", "w", encoding="utf-8") as f:
        f.write(out)
