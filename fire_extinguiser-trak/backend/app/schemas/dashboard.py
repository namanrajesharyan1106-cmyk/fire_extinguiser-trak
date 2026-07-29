from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_locations: int
    total_assets: int
    installed_assets: int
    unassigned_assets: int
    inspection_due_today: int
    inspection_completed_today: int
    open_maintenance: int
    expired_assets: int
    refill_due: int
    compliance_percent: float
    overdue_inspections: int


class MonthlyTrendItem(BaseModel):
    month: str
    inspections: int
    maintenance: int
    passed: int
    failed: int


class DepartmentStatsItem(BaseModel):
    department: str
    total_locations: int
    installed: int
    compliance: float


class RiskStatsItem(BaseModel):
    risk_category: str
    count: int
