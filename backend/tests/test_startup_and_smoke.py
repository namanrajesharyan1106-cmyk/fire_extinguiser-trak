import sys
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal

def test_startup_and_smoke():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200, f"/health endpoint returned {response.status_code}"
        
    from app.models import User
    from app.core.security import create_access_token
    
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.role == "ADMIN").first()
        assert admin_user is not None, "No ADMIN user found in DB."
        
        token = create_access_token(data={"sub": str(admin_user.id)})
    finally:
        db.close()
        
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/masters/active", headers=headers)
    assert response.status_code == 200, f"/api/masters/active endpoint returned {response.status_code}"
