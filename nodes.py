import uuid
import json
import urllib.request
from typing import List, Optional
from pydantic import BaseModel
from utils import get_env_safe

class NodeProtocol(BaseModel):
    candidate_name: str
    candidate_email: Optional[str] = None
    position: str
    questions: List[str]
    scheduled_at: str
    room_id: Optional[str] = None
    status: str = "PENDING"

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
        print(f"Supabase request failed: {e}")
        return []

def create_neural_node(node: NodeProtocol, user_id: str):
    """
    Initializes a new Secure Control Node.
    Generates a unique Room Signature and timestamps the entry.
    """
    body = {**node.dict(), "user_id": user_id, "room_id": str(uuid.uuid4())}
    result = _supabase_request("POST", "nodes", body)
    return result[0] if result else body

def get_active_streams(user_id: str = None):
    """
    Synchronizes with the active data streams from Supabase.
    """
    path = "nodes?select=*&order=created_at.desc"
    if user_id:
        path += f"&user_id=eq.{user_id}"
    return _supabase_request("GET", path)

def delete_node(room_id: str):
    """
    Purges a node from the neural buffer (Supabase).
    """
    _supabase_request("DELETE", f"nodes?room_id=eq.{room_id}")
    return True

def get_node_stats(user_id: str = None):
    """
    Calculates telemetry across all active nodes.
    """
    nodes = get_active_streams(user_id)
    total = len(nodes)
    active = sum(1 for n in nodes if n.get('status') == 'PENDING')
    completed = sum(1 for n in nodes if n.get('status') == 'COMPLETED')
    return {
        "total": total,
        "active": active,
        "completed": completed,
        "threats": 0 
    }
