import uuid
import json
from typing import List, Optional
from pydantic import BaseModel
from ..utils import get_env_safe
from ..supabase_client import supabase

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

async def create_neural_node(node: NodeProtocol, user_id: str):
    """Initializes a permanent control node."""
    body = {**node.dict(), "user_id": user_id, "room_id": str(uuid.uuid4())}
    result = await supabase.post("nodes", body)
    return result[0] if result else body

async def get_active_streams(user_id: str = None, since_date: str = None):
    """Returns only nodes that are NOT marked as deleted."""
    if not user_id: return []
    
    query = f"user_id=eq.{user_id}&order=created_at.desc"
    if since_date:
        query += f"&created_at=gte.{since_date}"
        
    all_nodes = await supabase.get("nodes", query)
    return [n for n in all_nodes if not n.get('is_deleted')]

async def get_node_by_room_id(room_id: str):
    """Fetches a specific node by its room_id."""
    result = await supabase.get("nodes", f"room_id=eq.{room_id}")
    return result[0] if result else None

async def delete_node(room_id: str):
    """Marks node as archived and COMPLETED."""
    await supabase.patch("nodes", f"room_id=eq.{room_id}", {
        "is_deleted": True,
        "status": "COMPLETED"
    })
    return True

async def get_node_stats(user_id: str = None, since_date: str = None):
    """Calculates usage telemetry asynchronously."""
    if not user_id: return {"total": 0, "active": 0, "completed": 0, "threats": 0}
    
    # 1. Fetch Latest Payment Date
    last_payment_date = None
    invoices = await supabase.get("invoices", f"user_id=eq.{user_id}&status=eq.PAID&order=created_at.desc&limit=1")
    if invoices:
        last_payment_date = invoices[0].get('created_at')

    # 2. Fetch Nodes with Date Filter
    query = f"user_id=eq.{user_id}"
    if since_date:
        query += f"&created_at=gte.{since_date}"
    elif last_payment_date:
        query += f"&created_at=gte.{last_payment_date}"
    
    all_relevant_nodes = await supabase.get("nodes", query)
    
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
