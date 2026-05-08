import sys
import os

# Add the project root to sys.path
sys.path.insert(0, r"c:\tist_integra")

try:
    from backend.routes import behavioral_routes
    print("✅ Import successful!")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
