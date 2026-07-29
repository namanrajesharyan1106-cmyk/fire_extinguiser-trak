from datetime import datetime

from ..models.asset import Asset


def is_asset_expired(asset: Asset) -> bool:
    if asset.expiry_date is None:
        return False
    return asset.expiry_date < datetime.utcnow().date()


def is_refill_overdue(asset: Asset) -> bool:
    if asset.refill_date is None:
        return False
    return asset.refill_date < datetime.utcnow().date()
