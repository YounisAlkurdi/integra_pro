import os
import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
try:
    from livekit.api import AccessToken, VideoGrants, LiveKitAPI, ListParticipantsRequest, DeleteRoomRequest
except ImportError:
    AccessToken = VideoGrants = LiveKitAPI = ListParticipantsRequest = DeleteRoomRequest = None
# nodes storage is handled via Supabase — see get_active_streams() below

# ── LiveKit Token Module ─────────────────────────────────────────────────────
# ⚠️  SECURITY:
#     LIVEKIT_API_KEY and LIVEKIT_API_SECRET are read here from .env (via dotenv
#     loaded in main.py). They are NEVER returned to the client — only a
#     short-lived signed JWT token is.
#
# v3 Fixes:
#   - Token TTL set to 30 minutes (1800s) — prevents long-lived tokens being abused
#   - Added DELETE /api/livekit/room/{roomName} endpoint so the dashboard can
#     forcibly terminate rooms via the LiveKit Server API
#   - Room Availability: Only grants tokens if the room is active or scheduled time has reached.
# ────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/livekit", tags=["LiveKit"])

VALID_ROLES   = {"hr", "candidate"}
TOKEN_TTL_SEC = 1800  # 30 minutes


class TokenRequest(BaseModel):
    roomName:        str
    participantName: str
    role:            str  # "hr" | "candidate"


def _build_token(api_key: str, api_secret: str, req: "TokenRequest") -> str:
    """
    LiveKit Token Factory.
    Generates a signed JWT that the frontend uses to join a LiveKit room.
    Token expires in TOKEN_TTL_SEC seconds and carries the participant's role
    as metadata.
    """
    if AccessToken is None:
        raise HTTPException(
            status_code=500,
            detail="LiveKit SDK not installed. Run: pip install livekit-api",
        )

    token = (
        AccessToken(api_key, api_secret)
        .with_identity(req.participantName)
        .with_name(req.participantName)
        .with_ttl(datetime.timedelta(seconds=TOKEN_TTL_SEC))
        .with_metadata(f'{{"role":"{req.role}"}}')
        .with_grants(
            VideoGrants(
                room_join=True,
                room=req.roomName,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )
    return token


@router.post("/token")
async def get_livekit_token(req: TokenRequest):
    """
    LiveKit Token Generator.
    Reads credentials from .env (backend only) and returns a signed JWT.

    Request body: { roomName, participantName, role }
    Response:     { token, url, roomName, participantName, role, ttl }
    """
    # --- Validation ---
    if not req.roomName.strip() or not req.participantName.strip():
        raise HTTPException(
            status_code=400,
            detail="roomName and participantName are required.",
        )

    if req.role.lower() not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}",
        )

    # --- Read secrets from env (NEVER return these to the client) ---
    api_key     = os.getenv("LIVEKIT_API_KEY")
    api_secret  = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured on the server.",
        )

    from nodes import get_node_by_room_id
    node = get_node_by_room_id(req.roomName)
    
    if not node:
        raise HTTPException(status_code=404, detail="Room not found.")

    if node.get('is_deleted') or node.get('status') == 'COMPLETED':
        msg_ar = "عذراً، هذا الرابط انتهت صلاحيته."
        msg_en = "Sorry, this session link has expired."
        raise HTTPException(status_code=410, detail=f"{msg_ar} | {msg_en}")
    
    if node:
        # 1. Check Schedule
        if node.get('scheduled_at'):
            try:
                sched_str = node['scheduled_at'].replace("Z", "+00:00")
                if len(sched_str) == 16: sched_str += ":00"
                scheduled_time = datetime.datetime.fromisoformat(sched_str)
                if scheduled_time.tzinfo is None:
                    scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
                now = datetime.datetime.now(datetime.timezone.utc)
                buffer = datetime.timedelta(minutes=5)
                
                if scheduled_time > (now + buffer):
                    wait_duration = scheduled_time - now
                    minutes = int(wait_duration.total_seconds() // 60)
                    msg_ar = f"الدخول متاح قبل 5 دقائق من الموعد. يرجى الانتظار {minutes} دقيقة."
                    msg_en = f"Access allowed 5m before start. Please wait {minutes} minutes."
                    raise HTTPException(status_code=403, detail=f"{msg_ar} | {msg_en}")
            except Exception as e:
                if isinstance(e, HTTPException): raise e
                print(f"[LiveKit] Schedule parsing error: {e}")

        # 2. Check Participant Limits (Subscription enforcement)
        max_p = node.get('max_participants', 2)
        if LiveKitAPI:
            try:
                lk_host = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
                async with LiveKitAPI(lk_host, api_key, api_secret) as lk_api:
                    p_list = await lk_api.room.list_participants(ListParticipantsRequest(room=req.roomName))
                    current_p = len(p_list.participants)
                    
                    if current_p >= max_p:
                        msg_ar = f"الغرفة ممتلئة. الحد الأقصى هو {max_p} مشاركين."
                        msg_en = f"Room is full. Maximum {max_p} participants allowed."
                        raise HTTPException(status_code=403, detail=f"{msg_ar} | {msg_en}")
            except Exception as e:
                if isinstance(e, HTTPException): raise e
                # If room doesn't exist yet (404), list_participants might fail. 
                # This is OK for token generation.
                if "not_found" in str(e).lower() or "404" in str(e):
                    pass 
                else:
                    print(f"[LiveKit] Limit check error: {e}")

        # --- 3. Admission Control (Lobby System) ---
        if req.role.lower() == "candidate":
            from nodes import _supabase_request
            existing_reqs = _supabase_request("GET", f"join_requests?room_id=eq.{req.roomName}&participant_name=eq.{req.participantName}&status=eq.APPROVED")
            
            if not existing_reqs:
                _supabase_request("POST", "join_requests", {
                    "room_id": req.roomName,
                    "participant_name": req.participantName,
                    "status": "PENDING"
                })
                return {
                    "status": "AWAITING_APPROVAL",
                    "message_ar": "بانتظار موافقة المحاور للدخول...",
                    "message_en": "Waiting for HR to approve your entry..."
                }

    # --- Generate token ---
    try:
        normalized_role = req.role.lower()
        
        # Calculate Dynamic TTL based on node limit (mins to secs) + 10m buffer for safety
        max_mins = node.get('max_duration_mins', 10) if node else 10
        dynamic_ttl = (max_mins * 60) + 600 # Add 10 mins buffer
        
        token_req = TokenRequest(
            roomName=req.roomName,
            participantName=req.participantName,
            role=normalized_role,
        )
        
        # Build token with dynamic TTL
        token = (
            AccessToken(api_key, api_secret)
            .with_identity(req.participantName)
            .with_name(req.participantName)
            .with_ttl(datetime.timedelta(seconds=dynamic_ttl))
            .with_metadata(f'{{"role":"{normalized_role}"}}')
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=req.roomName,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .to_jwt()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_out = traceback.format_exc()
        # Path updated to backend root for simplicity
        with open(os.path.join(os.path.dirname(__file__), "livekit_error.txt"), "w") as f:
            f.write(err_out)
        raise HTTPException(status_code=500, detail="Token generation failed.")

    return {
        "status":          "GRANTED",
        "token":           token,
        "url":             livekit_url,
        "roomName":        req.roomName,
        "participantName": req.participantName,
        "role":            normalized_role,
        "ttl":             dynamic_ttl,
    }


@router.get("/pending-requests/{room_id}")
async def get_pending_requests(room_id: str):
    from nodes import _supabase_request
    return _supabase_request("GET", f"join_requests?room_id=eq.{room_id}&status=eq.PENDING")


class DecisionRequest(BaseModel):
    room_id: str
    participant_name: str
    decision: str


@router.post("/decide-request")
async def decide_request(req: DecisionRequest):
    from nodes import _supabase_request
    _supabase_request("PATCH", f"join_requests?room_id=eq.{req.room_id}&participant_name=eq.{req.participant_name}&status=eq.PENDING", {
        "status": req.decision.upper()
    })
    return {"status": "UPDATED", "decision": req.decision}


@router.get("/request-status")
async def check_request_status(room_id: str, participant_name: str):
    from nodes import _supabase_request
    res = _supabase_request("GET", f"join_requests?room_id=eq.{room_id}&participant_name=eq.{participant_name}&order=created_at.desc")
    if res:
        return {"status": res[0]['status']}
    return {"status": "NOT_FOUND"}


@router.delete("/room/{room_name}")
async def end_room(room_name: str):
    """
    Force-terminate a LiveKit room.
    Kicks all participants and closes the room immediately.
    Called from the dashboard to end an active session.
    """
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://").replace("ws://", "http://")

    if not api_key or not api_secret or not livekit_url:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured on the server.",
        )

    if not DeleteRoomRequest:
        raise HTTPException(
            status_code=500,
            detail="LiveKit API SDK not installed.",
        )

    try:
        async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
            await lk_api.room.delete_room(DeleteRoomRequest(room=room_name))
        return {"deleted": True, "room": room_name}
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="LiveKit API SDK not installed. Run: pip install livekit-api",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete room: {str(e)}",
        )
