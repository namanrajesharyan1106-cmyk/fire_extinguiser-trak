import glob
import os

router_dir = r"c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\routers"

replacements = {
    "from .. import models, schemas, database, auth": "from .. import models, schemas\nfrom ..core import database, dependencies as auth",
    "from .. import models, schemas, auth, database": "from .. import models, schemas\nfrom ..core import database, dependencies as auth",
    "from ..services import auth_service, user_service, audit_service": "from ..services import auth_service, user_service\nfrom ..services.audit_service import log_audit_action",
    "Depends(database.get_db)": "Depends(database.get_db)",
}

for filepath in glob.glob(os.path.join(router_dir, "*.py")):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Generic replacements
    content = content.replace(
        "from .. import models, schemas, database, auth",
        "from .. import models, schemas\nfrom ..core import database, dependencies as auth",
    )
    content = content.replace(
        "from .. import models, schemas, auth, database",
        "from .. import models, schemas\nfrom ..core import database, dependencies as auth",
    )
    content = content.replace(
        "from ..utils import is_asset_expired, is_refill_overdue",
        "from ..utils.asset_checks import is_asset_expired, is_refill_overdue",
    )
    content = content.replace(
        "from ..constants import ", "from ..core.constants import "
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Import replacements done.")
