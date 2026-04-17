import os
import datetime
import logging
import traceback
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from ..core.supabase_client import get_supabase_client
from ..core.auth import get_current_user
from ..core.utils import get_env_safe
from backend.services.audit_logger import capture_event

try:
    from livekit.api import AccessToken, VideoGrants, LiveKitAPI, ListParticipantsRequest, DeleteRoomRequest
except ImportError:
    AccessToken = VideoGrants = LiveKitAPI = ListParticipantsRequest = DeleteRoomRequest = None

router = APIRouter(prefix="/livekit", tags=["LiveKit"])
logger = logging.getLogger(__name__)

VALID_ROLES = {"hr", "candidate"}
TOKEN_TTL_SEC = 1800

class TokenRequest(BaseModel):
    roomName: str
    participantName: str
    role: str

class DecisionRequest(BaseModel):
    room_id: str
    participant_name: str
    decision: str

async def get_node_by_room_id(room_id: str):
    """Retrieves node details from Supabase."""
    client = get_supabase_client()
    try:
        res = await client.from_("nodes").select("*").eq("room_id", room_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error fetching node {room_id}: {e}")
        return None

@router.post("/token")
async def get_livekit_token(req: TokenRequest, request: Request):
    """Generates a signed JWT for LiveKit."""
    if AccessToken is None:
        raise HTTPException(status_code=500, detail="LiveKit SDK not installed.")

    if not req.roomName.strip() or not req.participantName.strip():
        raise HTTPException(status_code=400, detail="roomName and participantName are required.")

    role = req.role.lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    api_key = get_env_safe("LIVEKIT_API_KEY")
    api_secret = get_env_safe("LIVEKIT_API_SECRET")
    livekit_url = get_env_safe("LIVEKIT_URL")

    node = await get_node_by_room_id(req.roomName)
    if not node:
        raise HTTPException(status_code=404, detail="Room not found.")

    if node.get('is_deleted') or node.get('status') == 'COMPLETED':
        raise HTTPException(status_code=410, detail="This session link has expired.")

    # Schedule check
    if node.get('scheduled_at'):
        try:
            sched_str = node['scheduled_at'].replace("Z", "+00:00")
            scheduled_time = datetime.datetime.fromisoformat(sched_str)
            now = datetime.datetime.now(datetime.timezone.utc)
            if scheduled_time > (now + datetime.timedelta(minutes=5)):
                wait_min = int((scheduled_time - now).total_seconds() // 60)
                raise HTTPException(status_code=403, detail=f"Access allowed 5m before start. Please wait {wait_min} minutes.")
        except HTTPException: raise
        except Exception as e:
            logger.error(f"Schedule parsing error: {e}")

    # Participant limits
    max_p = node.get('max_participants', 2)
    lk_host = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
    try:
        async with LiveKitAPI(lk_host, api_key, api_secret) as lk_api:
            p_list = await lk_api.room.list_participants(ListParticipantsRequest(room=req.roomName))
            if len(p_list.participants) >= max_p:
                raise HTTPException(status_code=403, detail=f"Room is full. Max {max_p} participants.")
    except HTTPException: raise
    except Exception as e:
        if "not_found" not in str(e).lower() and "404" not in str(e):
            logger.error(f"LiveKit limit check error: {e}")

    # Lobby System for candidates
    if role == "candidate":
        client = get_supabase_client()
        res = await client.from_("join_requests").select("*").eq("room_id", req.roomName).eq("participant_name", req.participantName).eq("status", "APPROVED").execute()
        
        if not res.data:
            # Create pending request if not exists
            await client.from_("join_requests").insert({
                "room_id": req.roomName,
                "participant_name": req.participantName,
                "status": "PENDING"
            }).execute()
            return {
                "status": "AWAITING_APPROVAL",
                "message_en": "Waiting for HR to approve your entry...",
                "message_ar": "بانتظار موافقة المحاور للدخول..."
            }

    # Generate Token
    max_mins = node.get('max_duration_mins', 10)
    ttl = (max_mins * 60) + 600
    
    try:
        token = (
            AccessToken(api_key, api_secret)
            .with_identity(req.participantName)
            .with_name(req.participantName)
            .with_ttl(datetime.timedelta(seconds=ttl))
            .with_metadata(f'{{"role":"{role}"}}')
            .with_grants(VideoGrants(room_join=True, room=req.roomName, can_publish=True, can_subscribe=True, can_publish_data=True))
            .to_jwt()
        )
        
        # Log join event
        capture_event("SYSTEM", "JOIN_ROOM", "livekit", req.roomName, {"participant": req.participantName, "role": role}, ip=request.client.host, ua=request.headers.get("user-agent", "unknown"))
        
        return {
            "status": "GRANTED",
            "token": token,
            "url": livekit_url,
            "roomName": req.roomName,
            "participantName": req.participantName,
            "role": role,
            "ttl": ttl
        }
    except Exception as e:
        logger.error(f"Token generation failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Token generation failed.")

@router.get("/pending-requests/{room_id}")
async def get_pending_requests(room_id: str, user: dict = Depends(get_current_user)):
    client = get_supabase_client()
    res = await client.from_("join_requests").select("*").eq("room_id", room_id).eq("status", "PENDING").execute()
    return res.data

@router.post("/decide-request")
async def decide_request(req: DecisionRequest, user: dict = Depends(get_current_user)):
    client = get_supabase_client()
    await client.from_("join_requests").update({"status": req.decision.upper()}).eq("room_id", req.room_id).eq("participant_name", req.participant_name).eq("status", "PENDING").execute()
    return {"status": "UPDATED", "decision": req.decision}

@router.get("/request-status")
async def check_request_status(room_id: str, participant_name: str):
    client = get_supabase_client()
    res = await client.from_("join_requests").select("status").eq("room_id", room_id).eq("participant_name", participant_name).order("created_at", desc=True).limit(1).execute()
    if res.data:
        return {"status": res.data[0]['status']}
    return {"status": "NOT_FOUND"}

@router.delete("/room/{room_name}")
async def end_room(room_name: str, request: Request, user: dict = Depends(get_current_user)):
    """Force-terminate a LiveKit room."""
    api_key = get_env_safe("LIVEKIT_API_KEY")
    api_secret = get_env_safe("LIVEKIT_API_SECRET")
    livekit_url = get_env_safe("LIVEKIT_URL").replace("wss://", "https://").replace("ws://", "http://")

    try:
        async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
            await lk_api.room.delete_room(DeleteRoomRequest(room=room_name))
        
        capture_event(user['sub'], "TERMINATE_ROOM", "livekit", room_name, ip=request.client.host, ua=request.headers.get("user-agent", "unknown"))
        return {"deleted": True, "room": room_name}
    except Exception as e:
        logger.error(f"Failed to delete room {room_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete room: {str(e)}")
