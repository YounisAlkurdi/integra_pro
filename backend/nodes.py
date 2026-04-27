import uuid
import json
import urllib.request
import urllib.parse
import urllib.error
import mimetypes
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
        encoded_query = urllib.parse.quote(query, safe='=&(),.!')
        path = f"{base}?{encoded_query}"

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
            return json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Neural Buffer HTTP Error {e.code}: {error_body}")
        return []
    except Exception as e:
        print(f"Neural Buffer Error: {e}")
        return []

def ensure_bucket_exists(bucket_name: str):
    """
    Tries to create a bucket if it doesn't exist.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "id": bucket_name,
        "name": bucket_name,
        "public": True
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except:
        pass # Already exists

def upload_to_supabase_storage(bucket: str, path: str, file_path: str):
    """
    Uploads a local file to Supabase Storage and returns the public URL.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None

    # Ensure bucket exists first
    ensure_bucket_exists(bucket)

    # 1. Read File
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
    except Exception as e:
        print(f"Storage Upload Failed (Read): {e}")
        return None

    # 2. Prepare Request
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    content_type, _ = mimetypes.guess_type(file_path)
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type or "application/octet-stream",
        "x-upsert": "true"
    }

    req = urllib.request.Request(url, data=file_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            # Successfully uploaded
            # Construct public URL (Assumes bucket is public)
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
            return public_url
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Storage Upload HTTP Error {e.code}: {error_body}")
        # If it fails, maybe it already exists or bucket missing
        return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
    except Exception as e:
        print(f"Storage Upload Failed: {e}")
        return None

def create_neural_node(node: NodeProtocol, user_id: str):
    """Initializes a permanent control node."""
    body = {**node.dict(), "user_id": user_id, "room_id": str(uuid.uuid4())}
    result = _supabase_request("POST", "nodes", body)
    return result[0] if result else body

def get_active_streams(user_id: str = None):
    """Returns only nodes that are NOT marked as deleted."""
    # Get everything for user and filter in memory for 100% reliability
    all_nodes = _supabase_request("GET", f"nodes?select=*&user_id=eq.{user_id}&order=created_at.desc") if user_id else []
    return [n for n in all_nodes if not n.get('is_deleted')]

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

def get_node_stats(user_id: str = None):
    """
    Calculates usage telemetry. 
    Neural Logic: Only counts nodes created AFTER the latest successful payment cycle.
    This ensures previous sub rooms or free rooms don't saturate new quotas.
    """
    if not user_id: return {"total": 0, "active": 0, "completed": 0, "threats": 0}
    
    # 1. Fetch Latest Payment Date
    last_payment_date = None
    invoices = _supabase_request("GET", f"invoices?user_id=eq.{user_id}&status=eq.PAID&order=created_at.desc&limit=1")
    if invoices:
        last_payment_date = invoices[0].get('created_at')

    # 2. Fetch Nodes with Date Filter if payment exists
    node_query = f"nodes?select=status,is_deleted,created_at&user_id=eq.{user_id}"
    if last_payment_date:
        # filter nodes >= last_payment_date
        node_query += f"&created_at=gte.{last_payment_date}"
    
    all_relevant_nodes = _supabase_request("GET", node_query)
    
    total_consumed = len(all_relevant_nodes)
    active_now = [n for n in all_relevant_nodes if not n.get('is_deleted')]
    
    pending = sum(1 for n in active_now if n.get('status') == 'PENDING')
    completed = sum(1 for n in active_now if n.get('status') == 'COMPLETED')
    
    return {
        "total": total_consumed, 
        "active_view": len(active_now),
        "active": pending,
        "completed": completed,
        "threats": 0 
    }
