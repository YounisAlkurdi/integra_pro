import uuid
import json
import urllib.request
import urllib.parse
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
    max_duration_mins: Optional[int] = 10
    max_participants: Optional[int] = 2

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_SERVICE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

def _supabase_request(method: str, path: str, body=None):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return []

    if '?' in path:
        base, query = path.split('?', 1)
        # Add * + : and other symbols for PostgREST compatibility
        encoded_query = urllib.parse.quote(query, safe='=&(),.!+:*')
        path = f"{base}?{encoded_query}"

    url = f"{SUPABASE_URL}/rest/v1/{path}"
    # Log the debug URL to catch the exact cause if it fails
    # print(f"[DEBUG] Supabase URL: {url}")
    
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
            return json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Neural Buffer Error (HTTP {e.code}): {error_body}")
        return []
    except Exception as e:
        print(f"Neural Buffer Error: {e}")
        return []

def create_neural_node(node: NodeProtocol, user_id: str):
    """Initializes a permanent control node."""
    body = {**node.dict(), "user_id": user_id, "room_id": str(uuid.uuid4())}
    result = _supabase_request("POST", "nodes", body)
    return result[0] if result else body

def get_active_streams(user_id: str = None, since_date: str = None, active_rooms_map: dict = None):
    """Returns only nodes that are NOT marked as deleted, optionally filtered by date."""
    query = f"nodes?select=*&user_id=eq.{user_id}&order=created_at.desc"
    if since_date:
        # Ultra-defensive sanitization for corrupted timestamps (e.g. from broken JSON strings)
        # Take only the standard ISO8601 part, stop at spaces or plus signs
        import re
        match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', since_date)
        if match:
            clean_date = match.group(0)
            query += f"&created_at=gte.{clean_date}"
        else:
            # Fallback if regex fails but we have a value
            clean_date = since_date.split(' ')[0].split('+')[0]
            query += f"&created_at=gte.{clean_date}"
    
    all_nodes = _supabase_request("GET", query) if user_id else []
    
    results = []
    for n in all_nodes:
        if not n.get('is_deleted'):
            # Add virtual live flag based on LiveKit reality
            rid = n.get('room_id')
            if active_rooms_map and rid in active_rooms_map:
                n['is_live'] = True
                n['participants_count'] = active_rooms_map[rid]
            else:
                n['is_live'] = False
                n['participants_count'] = 0
            results.append(n)
    return results

def get_node_by_room_id(room_id: str):
    """Fetches a specific node by its room_id without user_id filtering."""
    result = _supabase_request("GET", f"nodes?select=*&room_id=eq.{room_id}")
    return result[0] if result else None

def delete_node(room_id: str):
    """Marks node as archived and COMPLETED. Does NOT remove record."""
    _supabase_request("PATCH", f"nodes?room_id=eq.{room_id}", {
        "is_deleted": True,
        "status": "COMPLETED"
    })
    return True

def get_node_stats(user_id: str = None, since_date: str = None, active_rooms_map: dict = None):
    """
    Calculates usage telemetry within a specific period.
    """
    if not user_id: return {"total": 0, "active": 0, "completed": 0, "threats": 0}
    
    query = f"nodes?select=status,is_deleted,created_at,room_id&user_id=eq.{user_id}"
    if since_date:
        # Ultra-defensive sanitization
        import re
        match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', since_date)
        if match:
            clean_date = match.group(0)
            query += f"&created_at=gte.{clean_date}"
        else:
            clean_date = since_date.split(' ')[0].split('+')[0]
            query += f"&created_at=gte.{clean_date}"
        
    all_relevant_nodes = _supabase_request("GET", query)
    
    if not all_relevant_nodes:
        return {"total": 0, "active": 0, "completed": 0, "threats": 0}

    total_consumed = len(all_relevant_nodes)
    
    # Live count is based on the provided active_rooms_map from LiveKit Server
    live_count = 0
    if active_rooms_map:
        # Count how many of THIS user's active rooms are in the map
        user_room_ids = {n.get('room_id') for n in all_relevant_nodes if not n.get('is_deleted')}
        live_count = sum(1 for rid in active_rooms_map.keys() if rid in user_room_ids)
    
    # Completed is based on DB status
    completed = sum(1 for n in all_relevant_nodes if n.get('status') == 'COMPLETED')
    
    return {
        "total": total_consumed, 
        "active": live_count,
        "completed": completed,
        "threats": 0 
    }
