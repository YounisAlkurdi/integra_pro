import json
import urllib.request
from typing import List, Optional
from pydantic import BaseModel
from utils import get_env_safe

class ChatLogEntry(BaseModel):
    node_id: str
    sender: str
    message: str

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_SERVICE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

def _supabase_request(method: str, path: str, body=None):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("WARNING: Supabase URL or Service Key missing.")
        return []

    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            if content:
                return json.loads(content)
            return []
    except Exception as e:
        print(f"Supabase Log Request Failed: {e}")
        return []

def save_chat_log(log: ChatLogEntry, user_id: str):
    """
    Saves a single transcript segment to the database.
    """
    body = {
        "node_id": log.node_id,
        "sender": log.sender,
        "message": log.message,
        "user_id": user_id
    }
    return _supabase_request("POST", "chat_logs", body)

def get_node_chat_logs(node_id: str, user_id: str):
    """
    Retrieves all transcript segments for a particular interview.
    """
    path = f"chat_logs?node_id=eq.{node_id}&user_id=eq.{user_id}&order=timestamp.asc"
    return _supabase_request("GET", path)
