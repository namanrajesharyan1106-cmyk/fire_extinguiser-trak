"""
Test suite for enhanced Dashboard API endpoints:
- Date filtering (Today, This Month, Custom ranges, Empty ranges)
- Monthly trends with date range
- Inspection status distribution
- Overdue inspections
- Recent maintenance
- Recent activity
- Preserved master inventory counts
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app import models
from app.core import security

client = TestClient(app)

@pytest.fixture(scope="module")
def admin_token():
    db = SessionLocal()
    try:
        # Find an admin user or use default
        user = db.query(models.User).filter(models.User.role == "ADMIN").first()
        if not user:
            user = db.query(models.User).first()
        token = security.create_access_token(data={"sub": str(user.id)})

        # Ensure July 2026 inspections exist for tests
        july_count = db.query(models.Inspection).filter(
            models.Inspection.inspection_date >= datetime(2026, 7, 1),
            models.Inspection.inspection_date <= datetime(2026, 7, 31, 23, 59, 59)
        ).count()
        if july_count < 12:
            loc = db.query(models.Location).first()
            asset = db.query(models.Asset).first()
            if loc and asset:
                for i in range(12 - july_count):
                    st = "Pass" if i < 9 else "Fail"
                    insp = models.Inspection(
                        location_id=loc.location_id,
                        asset_id=asset.asset_id,
                        inspection_date=datetime(2026, 7, 15, 10, i),
                        overall_status=st,
                        inspector="Tester"
                    )
                    db.add(insp)
                db.commit()

        return token
    finally:
        db.close()

@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

def test_dashboard_stats_default(auth_headers):
    """Test standard /api/dashboard/stats without date filters (backward compatibility)."""
    response = client.get("/api/dashboard/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_assets" in data
    assert "total_locations" in data
    assert "installed_assets" in data
    assert "compliance_percent" in data
    assert data["total_assets"] >= 0
    assert data["total_locations"] >= 0

def test_dashboard_stats_today_filter(auth_headers):
    """Test date filter for Today."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    response = client.get(f"/api/dashboard/stats?start_date={today_str}&end_date={today_str}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == today_str
    assert data["end_date"] == today_str
    # Master counts are preserved
    assert data["total_assets"] > 0
    assert data["total_locations"] > 0

def test_dashboard_stats_date_range_july_2026(auth_headers):
    """Test custom date range filtering (July 2026 where inspection records exist)."""
    response = client.get("/api/dashboard/stats?start_date=2026-07-01&end_date=2026-07-31", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["inspections_in_range"] == 12
    assert data["inspections_passed"] == 9
    assert data["inspections_failed"] == 3

def test_dashboard_stats_empty_date_range(auth_headers):
    """Test date range with no records (returns 0 for range metrics, keeps master counts)."""
    response = client.get("/api/dashboard/stats?start_date=2020-01-01&end_date=2020-01-31", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["inspections_in_range"] == 0
    assert data["inspections_passed"] == 0
    assert data["inspections_failed"] == 0
    assert data["total_assets"] > 0
    assert data["total_locations"] > 0

def test_monthly_trend_date_filtered(auth_headers):
    """Test /api/dashboard/monthly-trend with start_date and end_date."""
    response = client.get("/api/dashboard/monthly-trend?start_date=2026-07-01&end_date=2026-11-16", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    months = [item["month"] for item in data]
    assert "Jul 2026" in months
    assert "Nov 2026" in months
    # Verify July data has inspections
    july_data = next((item for item in data if item["month"] == "Jul 2026"), None)
    assert july_data is not None
    assert july_data["inspections"] == 12
    assert july_data["passed"] == 9
    assert july_data["failed"] == 3

def test_inspection_status_distribution(auth_headers):
    """Test /api/dashboard/inspection-status-distribution endpoint."""
    response = client.get("/api/dashboard/inspection-status-distribution?start_date=2026-07-01&end_date=2026-07-31", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    statuses = {item["status"]: item["count"] for item in data}
    assert "Pass" in statuses
    assert "Fail" in statuses
    assert statuses["Pass"] == 9
    assert statuses["Fail"] == 3

def test_overdue_inspections(auth_headers):
    """Test /api/dashboard/overdue-inspections endpoint."""
    response = client.get("/api/dashboard/overdue-inspections?limit=5", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        first = data[0]
        assert "location_id" in first
        assert "location_name" in first
        assert "days_overdue" in first

def test_recent_maintenance(auth_headers):
    """Test /api/dashboard/recent-maintenance endpoint."""
    response = client.get("/api/dashboard/recent-maintenance?limit=5", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        ticket = data[0]
        assert "maintenance_id" in ticket
        assert "status" in ticket
        assert "priority" in ticket

def test_recent_activity(auth_headers):
    """Test /api/dashboard/recent-activity endpoint."""
    response = client.get("/api/dashboard/recent-activity?limit=5", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "activity" in data["data"]
