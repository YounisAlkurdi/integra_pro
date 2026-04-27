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

def save_chat_log(log: ChatLogEntry, user_id: Optional[str] = None):
    """
    Saves a single transcript segment. 
    If user_id is missing (candidate logging), we derive it from the room owner.
    """
    actual_user_id = user_id
    
    if not actual_user_id:
        # Candidate is logging. Find the owner of this room.
        node_info = _supabase_request("GET", f"nodes?room_id=eq.{log.node_id}&select=user_id")
        if node_info and len(node_info) > 0:
            actual_user_id = node_info[0].get("user_id")
    
    if not actual_user_id:
        print(f"❌ Log Error: No owner found for room {log.node_id}. Log discarded.")
        return []

    body = {
        "room_id": log.node_id, 
        "sender": log.sender,
        "message": log.message,
        "user_id": actual_user_id
    }
    return _supabase_request("POST", "chat_logs", body)

def get_node_chat_logs(node_id: str, user_id: str):
    """
    Retrieves all transcript segments for a particular interview.
    """
    path = f"chat_logs?room_id=eq.{node_id}&user_id=eq.{user_id}&order=created_at.asc"
    return _supabase_request("GET", path)
