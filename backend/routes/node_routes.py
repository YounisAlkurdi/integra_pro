from fastapi import APIRouter, Depends, HTTPException
from ..auth import get_current_user, get_user_profile_data
from ..nodes import NodeProtocol, create_neural_node, get_active_streams, get_node_stats, delete_node, purge_completed_nodes, get_signed_video_url, get_interview_report

router = APIRouter(prefix="/api/nodes", tags=["Nodes"])

@router.post("")
async def create_node(node: NodeProtocol, user: dict = Depends(get_current_user)):
    """Secure Node Initialization with Subscription Enforcement."""
    profile = await get_user_profile_data(user)
    sub = profile.get("subscription") or {}
    limit = sub.get('interviews_limit', 5)
    
    # 1. Enforce limits from the subscription plan on the record
    node.max_participants = sub.get("max_participants", 2)
    node.max_duration_mins = sub.get("max_duration_mins", 10)
    
    # 2. Check Usage Limit
    stats = await get_node_stats(user_id=user["sub"])
    if stats['total'] >= limit:
        raise HTTPException(status_code=402, detail="Neural Link Saturated: Limit Reached")
        
    return await create_neural_node(node, user_id=user["sub"])

@router.get("")
async def list_nodes(user: dict = Depends(get_current_user)):
    """Data Stream Synchronization."""
    return await get_active_streams(user_id=user["sub"])

@router.delete("/purge/completed")
async def purge_nodes(user: dict = Depends(get_current_user)):
    """Bulk Soft-Delete Protocol for Completed Nodes."""
    count = await purge_completed_nodes(user_id=user["sub"])
    return {"status": "PURGED", "count": count}

@router.delete("/{room_id}")
async def remove_node(room_id: str, user: dict = Depends(get_current_user)):
    """Node Deletion Protocol."""
    if await delete_node(room_id):
        return {"status": "PURGED", "room_id": room_id}
    raise HTTPException(status_code=404, detail="Node not found")

@router.get("/stats")
async def sys_stats(user: dict = Depends(get_current_user)):
    """Telemetry Reporting Node."""
    return await get_node_stats(user_id=user["sub"])

@router.get("/signed-video-url")
async def signed_video_url(video_path: str, user: dict = Depends(get_current_user)):
    """
    Generates a secure, time-limited Signed URL for a verification video.
    Validates that the video belongs to the requesting user's node.
    """
    url = await get_signed_video_url(video_path=video_path, user_id=user["sub"])
    if not url:
        raise HTTPException(status_code=403, detail="Access Denied or video not found")
    return {"signed_url": url}

@router.get("/{room_id}/report")
async def get_room_report(room_id: str, user: dict = Depends(get_current_user)):
    """Fetches the AI-generated interview report for a specific room."""
    report = await get_interview_report(room_id=room_id, user_id=user["sub"])
    return report or {}
