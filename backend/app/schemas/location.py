from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

# Type alias for stripped strings with max length
StrictStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
OptionalStr = Annotated[
    Optional[str], StringConstraints(strip_whitespace=True, max_length=100)
]


class LocationBase(BaseModel):
    location_id: OptionalStr = Field(None, description="Unique ID for location")
    location_code: OptionalStr = None
    location_name: StrictStr = Field(..., description="Name of the location")
    plant: OptionalStr = None
    area: OptionalStr = None
    department: OptionalStr = None
    building: OptionalStr = None
    floor: OptionalStr = None
    machine: OptionalStr = None
    risk_category: OptionalStr = "Medium"
    qr_code: OptionalStr = None
    status: OptionalStr = "Active"
    inspection_frequency: Optional[int] = Field(30, ge=1, le=365)
    gps_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    gps_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)


class LocationCreate(LocationBase):
    location_id: Optional[str] = Field(
        None,
        description="Unique ID — auto-generated if not provided",
    )
    required_asset_type_id: int
    required_capacity_id: int


class LocationUpdate(BaseModel):
    location_code: OptionalStr = None
    location_name: Optional[StrictStr] = None
    plant: OptionalStr = None
    area: OptionalStr = None
    department: OptionalStr = None
    building: OptionalStr = None
    floor: OptionalStr = None
    machine: OptionalStr = None
    required_asset_type_id: Optional[int] = None
    required_capacity_id: Optional[int] = None
    risk_category: OptionalStr = None
    status: OptionalStr = None
    inspection_frequency: Optional[int] = Field(None, ge=1, le=365)
    gps_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    gps_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)


class LocationResponse(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    required_asset_type: Optional[str] = None
    required_capacity: Optional[str] = None
    required_asset_type_id: Optional[int] = None
    required_capacity_id: Optional[int] = None
    max_assets: Optional[int] = 15
    current_assets_count: Optional[int] = 0
    remaining_capacity: Optional[int] = 15
    qr_image_path: Optional[str] = None
    last_inspection_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None


class PaginatedLocationResponse(BaseModel):
    items: List[LocationResponse]
    total: int
