"""
Nodes Route — Integra SaaS
Handles neural node (interview) lifecycle.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from backend.core.supabase_client import supabase
from backend.core.auth import get_current_user
from backend.core.rate_limit import standard_limit

from backend.services.audit_logger import capture_event

router = APIRouter(prefix="/nodes", tags=["Neural Nodes"])

class NodeProtocol(BaseModel):
    candidate_name: str
    candidate_email: Optional[str] = None
    position: str
    questions: List[str]
    scheduled_at: str

async def get_node_stats(user_id: str, since_date: Optional[str] = None):
    # Ensure user_id is correct
    query = f"user_id=eq.{user_id}"
    if since_date:
        query += f"&created_at=gte.{since_date}"
    
    # Use the supabase client helper
    res = await supabase.get("nodes", query, cache_ttl=60)
    return {
        "total": len(res),
        "active": len([r for r in res if r.get('status') == 'active']),
        "completed": len([r for r in res if r.get('status') == 'completed'])
    }

async def get_active_streams(user_id: str):
    """Alias for listing active nodes."""
    return await supabase.get("nodes", f"user_id=eq.{user_id}&status=eq.active")

async def create_neural_node(protocol: NodeProtocol, user_id: str, ip: str = "unknown", ua: str = "unknown"):
    import uuid
    room_id = str(uuid.uuid4())
    data = {
        "user_id": user_id,
        "room_id": room_id,
        "candidate_name": protocol.candidate_name,
        "candidate_email": protocol.candidate_email,
        "position": protocol.position,
        "questions": protocol.questions,
        "scheduled_at": protocol.scheduled_at,
        "status": "active"
    }
    res = await supabase.post("nodes", data)
    capture_event(user_id, "CREATE", "node", room_id, {"candidate": protocol.candidate_name, "position": protocol.position}, ip=ip, ua=ua)
    return res

async def delete_node(room_id: str, user_id: str = None):
    """Internal helper to delete a node, optionally scoped by user."""
    path = f"nodes?room_id=eq.{room_id}"
    if user_id:
        path += f"&user_id=eq.{user_id}"
    
    try:
        await supabase.request("DELETE", path)
        return True
    except Exception as e:
        print(f"Delete Error: {e}")
        return False

# Routes...
@router.get("/", response_model=List[dict])
async def list_nodes(user: dict = Depends(get_current_user)):
    """Data Stream Synchronization."""
    return await supabase.get("nodes", f"user_id=eq.{user['sub']}&order=created_at.desc")

@router.post("/", dependencies=[Depends(standard_limit)])
async def create_node(node: NodeProtocol, request: Request, user: dict = Depends(get_current_user)):
    """Secure Node Initialization with Subscription Enforcement."""
    user_id = user["sub"]
    
    # 1. Check Usage Limit (Simple check for now)
    stats = await get_node_stats(user_id=user_id)
    # Note: In a full SaaS, we'd check against the user's specific plan limit here.
    # For now, we'll allow it if total < 50 (demo limit)
    if stats['total'] >= 50:
        raise HTTPException(status_code=402, detail="Neural Link Saturated: Limit Reached")
        
    return await create_neural_node(
        node, 
        user_id=user_id, 
        ip=request.client.host if request.client else "unknown",
        ua=request.headers.get("user-agent", "unknown")
    )

@router.delete("/{room_id}")
async def remove_node(room_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Node Deletion Protocol."""
    # Verify ownership then delete
    success = await delete_node(room_id, user_id=user['sub'])
    if success:
        capture_event(user['sub'], "DELETE", "node", room_id, ip=request.client.host, ua=request.headers.get("user-agent", "unknown"))
        return {"status": "PURGED", "room_id": room_id}
    raise HTTPException(status_code=404, detail="Node not found or deletion failed")

@router.get("/stats")
async def sys_stats(user: dict = Depends(get_current_user)):
    """Telemetry Reporting Node."""
    return await get_node_stats(user_id=user["sub"])
