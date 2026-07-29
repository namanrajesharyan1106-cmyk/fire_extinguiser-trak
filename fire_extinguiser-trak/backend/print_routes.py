import sys
from app.main import app

def print_routes():
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"{route.methods} {route.path}")

if __name__ == "__main__":
    print_routes()
