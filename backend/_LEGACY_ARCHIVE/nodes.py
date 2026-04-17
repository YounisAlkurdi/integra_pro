import json
import uuid
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from .supabase_client import supabase
from .utils import cache

class NodeProtocol(BaseModel):
    candidate_name: str
    position: str
    candidate_email: Optional[str] = None
    scheduled_at: Optional[str] = None
    questions: Optional[List[str]] = None
    max_participants: int = 2
    max_duration_mins: int = 10

async def create_neural_node(node: NodeProtocol, user_id: str) -> Dict[str, Any]:
    """Initialize a new interview node session in Supabase."""
    room_id = f"integra_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "room_id": room_id,
        "user_id": user_id,
        "candidate_name": node.candidate_name,
        "position": node.position,
        "candidate_email": node.candidate_email,
        "scheduled_at": node.scheduled_at,
        "questions": node.questions or [],
        "max_participants": node.max_participants,
        "max_duration_mins": node.max_duration_mins,
        "status": "active",
        "created_at": "now()"
    }
    
    await supabase.post("nodes", payload)
    return {"status": "ACTIVE", "room_id": room_id, "node": payload}

async def get_active_streams(user_id: str, since_date: str = None) -> List[Dict[str, Any]]:
    """Retrieve all active nodes for a user."""
    query = f"user_id=eq.{user_id}&status=eq.active"
    if since_date:
        query += f"&created_at=gte.{since_date}"
    query += "&order=created_at.desc"
    return await supabase.get("nodes", query)

async def get_node_by_room_id(room_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific node by its room ID."""
    res = await supabase.get("nodes", f"room_id=eq.{room_id}")
    return res[0] if res else None

async def get_node_stats(user_id: str, since_date: str = None) -> Dict[str, Any]:
    """Calculate usage stats for limit enforcement."""
    # Use cache for stats
    cache_key = f"stats:{user_id}:{since_date or ''}"
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    query = f"user_id=eq.{user_id}"
    if since_date:
        query += f"&created_at=gte.{since_date}"
        
    nodes = await supabase.get("nodes", query)
    total = len(nodes)
    active = len([n for n in nodes if n.get('status') == 'active'])
    completed = total - active
    
    res = {
        "total": total,
        "active": active,
        "completed": completed
    }
    cache.set(cache_key, res, ttl=60) # Cache stats for 1 minute
    return res

async def delete_node(room_id: str) -> bool:
    """Soft delete or purge a node session."""
    try:
        await supabase.patch("nodes", f"room_id=eq.{room_id}", {"status": "purged"})
        return True
    except:
        return False
