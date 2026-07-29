import sys
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal

def run_tests():
    print("--- Backend Startup Test ---")
    try:
        client = TestClient(app)
        print("[OK] FastAPI app instantiated and TestClient created.")
    except Exception as e:
        print(f"[FAIL] Failed to startup app: {e}")
        sys.exit(1)

    print("--- Backend Smoke Test ---")
    try:
        response = client.get("/health")
        if response.status_code == 200:
            print("[OK] /health endpoint returned 200.")
        else:
            print(f"[FAIL] /health endpoint returned {response.status_code}.")
            sys.exit(1)
            
        from app.models import User
        from app.core.security import create_access_token
        
        db = SessionLocal()
        admin_user = db.query(User).filter(User.role == "ADMIN").first()
        if not admin_user:
            print("[FAIL] No ADMIN user found in DB.")
            sys.exit(1)
            
        token = create_access_token(data={"sub": str(admin_user.id)})
        db.close()
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/masters/active", headers=headers)
        if response.status_code == 200:
            print("[OK] /api/masters/active endpoint returned 200.")
            data = response.json().get("data", {})
            print(f"     Found {len(data.get('plants', []))} active plants.")
        else:
            print(f"[FAIL] /api/masters/active endpoint returned {response.status_code}.")
            print(response.text)
            sys.exit(1)
            
        print("Backend Tests Passed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FAIL] Smoke test exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
