import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/")
print("Health check:", response.status_code, response.json())

response_config = client.get("/config")
print("Config check:", response_config.status_code, response_config.json())
