import os
import requests
import json
import sys
from dotenv import load_dotenv

def verify():
    print("=== INTEGRA SYSTEM CONNECTIVITY AUDIT ===")
    load_dotenv()
    
    # 1. Check Env Vars
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_JWT_SECRET"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"[ERROR] Missing Environment Variables: {', '.join(missing)}")
    else:
        print("[OK] Core Environment Variables Loaded.")

    # 2. Check Backend Health
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Backend Core Online: {response.json().get('status')}")
        else:
            print(f"[WARNING] Backend returned status code: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Backend Connectivity Failed: {e}")
        print("      => Ensure you ran: uvicorn backend.main:app --reload --port 8000")

    # 3. Check Supabase Connectivity
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if url and key:
        try:
            # Simple check to Supabase Auth Health
            resp = requests.get(f"{url}/auth/v1/health", timeout=5)
            if resp.status_code == 200:
                print("[OK] Supabase Cloud Connection Established.")
            else:
                print(f"[WARNING] Supabase Health Check status: {resp.status_code}")
        except Exception as e:
            print(f"[ERROR] Supabase Reachability Failure: {e}")

    # 4. Check Frontend Files
    pages = ["index.html", "login.html", "dashboard.html"]
    for page in pages:
        path = f"frontend/pages/{page}"
        if os.path.exists(path):
            print(f"[OK] Frontend Page Found: {page}")
        else:
            print(f"[ERROR] Missing Critical File: {path}")

    print("==========================================")
    print("Ready for Deployment Operations.")

if __name__ == "__main__":
    verify()
