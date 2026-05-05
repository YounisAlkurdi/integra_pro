import os
import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..nodes import get_node_by_room_id
from ..services.database_service import db

try:
    from livekit.api import AccessToken, VideoGrants, LiveKitAPI, ListParticipantsRequest, DeleteRoomRequest
except ImportError:
    AccessToken = VideoGrants = LiveKitAPI = ListParticipantsRequest = DeleteRoomRequest = None

# ── LiveKit Token Module ─────────────────────────────────────────────────────
# ⚠️  SECURITY:
#     LIVEKIT_API_KEY and LIVEKIT_API_SECRET are read here from .env
#     They are NEVER returned to the client — only a short-lived signed JWT token is.
# ────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/livekit", tags=["LiveKit"])

VALID_ROLES   = {"hr", "candidate"}
TOKEN_TTL_SEC = 1800  # 30 minutes


class TokenRequest(BaseModel):
    roomName:        str
    participantName: str
    role:            str  # "hr" | "candidate"


@router.post("/token")
async def get_livekit_token(req: TokenRequest):
    """
    LiveKit Token Generator.
    Reads credentials from .env (backend only) and returns a signed JWT.
    """
    # --- Validation ---
    if not req.roomName.strip() or not req.participantName.strip():
        raise HTTPException(status_code=400, detail="roomName and participantName are required.")

    if req.role.lower() not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    # --- Read secrets from env ---
    api_key     = os.getenv("LIVEKIT_API_KEY")
    api_secret  = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured on the server.")

    node = await get_node_by_room_id(req.roomName)
    
    if not node:
        raise HTTPException(status_code=404, detail="Room not found.")

    if node.get('is_deleted') or node.get('status') == 'COMPLETED':
        msg_ar = "عذراً، هذا الرابط انتهت صلاحيته."
        msg_en = "Sorry, this session link has expired."
        raise HTTPException(status_code=410, detail=f"{msg_ar} | {msg_en}")
    
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

    # 2. Check Participant Limits
    max_p = node.get('max_participants', 2)
    if LiveKitAPI:
        try:
            lk_host = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
            async with LiveKitAPI(lk_host, api_key, api_secret) as lk_api:
                p_list = await lk_api.room.list_participants(ListParticipantsRequest(room=req.roomName))
                current_p = len(p_list.participants)
                
                if req.role.lower() == "candidate":
                    candidate_count = 0
                    for p in p_list.participants:
                        if p.metadata and '"role":"candidate"' in p.metadata and p.identity != req.participantName:
                            candidate_count += 1
                    
                    if candidate_count >= 1:
                        msg_ar = "عذراً، يوجد مرشح آخر داخل الغرفة بالفعل."
                        msg_en = "Sorry, another candidate is already in the room."
                        raise HTTPException(status_code=403, detail=f"{msg_ar} | {msg_en}")

                if current_p >= max_p:
                    msg_ar = f"الغرفة ممتلئة. الحد الأقصى هو {max_p} مشاركين."
                    msg_en = f"Room is full. Maximum {max_p} participants allowed."
                    raise HTTPException(status_code=403, detail=f"{msg_ar} | {msg_en}")
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            if "not_found" in str(e).lower() or "404" in str(e): pass 
            else: print(f"[LiveKit] Limit check error: {e}")

    # 3. Admission Control (Lobby System)
    if req.role.lower() == "candidate":
        # Check for ANY existing request
        existing_reqs = await db.client.table("join_requests") \
            .select("*") \
            .eq("room_id", req.roomName) \
            .eq("participant_name", req.participantName) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if existing_reqs.data:
            req_obj = existing_reqs.data[0]
            
            # --- SECURITY GATE: Mandatory Deepfake Verification ---
            # Even if status is APPROVED, if they aren't VERIFIED, they stay in lobby
            # UNLESS an explicit HR Override was granted.
            is_overridden = req_obj.get('is_override', False)
            if req_obj['status'] != 'APPROVED' or (req_obj.get('liveness_status') != 'VERIFIED' and not is_overridden):
                return {
                    "status": "AWAITING_APPROVAL",
                    "request_id": req_obj['id'],
                    "liveness_status": req_obj.get('liveness_status', 'PENDING'),
                    "is_overridden": is_overridden,
                    "message_ar": "بانتظار التحقق من الهوية وموافقة المحاور..." if not is_overridden else "تم تجاوز التحقق من قبل المحاور. جاري الدخول...",
                    "message_en": "Waiting for identity verification and HR approval..." if not is_overridden else "Verification bypassed by HR. Joining...",
                    "nudge_count": req_obj.get('nudge_count', 0)
                }
        else:
            # Create new PENDING request
            new_req = await db.client.table("join_requests").insert({
                "room_id": req.roomName,
                "participant_name": req.participantName,
                "status": "PENDING"
            }).execute()
            
            req_id = new_req.data[0]['id'] if new_req.data else None
            
            return {
                "status": "AWAITING_APPROVAL",
                "request_id": req_id,
                "liveness_status": "PENDING",
                "message_ar": "بانتظار موافقة المحاور للدخول...",
                "message_en": "Waiting for HR to approve your entry..."
            }

    # --- Generate token ---
    try:
        normalized_role = req.role.lower()
        max_mins = node.get('max_duration_mins', 10) if node else 10
        dynamic_ttl = (max_mins * 60) + 600
        
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
        
    except Exception as e:
        print(f"[LiveKit] Token generation failed: {e}")
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
    res = await db.client.table("join_requests").select("*").eq("room_id", room_id).eq("status", "PENDING").execute()
    return res.data


class DecisionRequest(BaseModel):
    room_id: str
    participant_name: str
    decision: str
    is_override: bool = False
    override_reason: str = None

class NudgeRequest(BaseModel):
    request_id: str

@router.post("/nudge-candidate")
async def nudge_candidate(req: NudgeRequest):
    """Increment nudge count to trigger UI alert on candidate side."""
    await db.client.rpc("increment_nudge", {"row_id": req.request_id}).execute()
    return {"status": "NUDGED"}


@router.post("/decide-request")
async def decide_request(req: DecisionRequest):
    """
    HR decision to allow or block a candidate.
    Must ensure the candidate is VERIFIED before approving.
    """
    # 1. Fetch current liveness status
    res = await db.client.table("join_requests") \
        .select("liveness_status") \
        .eq("room_id", req.room_id) \
        .eq("participant_name", req.participant_name) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Join request not found.")
    
    liveness = res.data[0].get("liveness_status", "PENDING")

    # 2. Prevent approval if not verified (unless overridden)
    if req.decision.upper() == "APPROVED" and liveness != "VERIFIED" and not req.is_override:
        raise HTTPException(
            status_code=403, 
            detail="Security Block: Candidate must be VERIFIED by Gatekeeper before approval can be granted. Use Override if necessary."
        )

    # 3. Update status
    update_data = {"status": req.decision.upper()}
    if req.is_override:
        update_data["is_override"] = True
        update_data["override_reason"] = req.override_reason or "No reason provided"

    await db.client.table("join_requests") \
        .update(update_data) \
        .eq("room_id", req.room_id) \
        .eq("participant_name", req.participant_name) \
        .eq("status", "PENDING") \
        .execute()
        
    return {"status": "UPDATED", "decision": req.decision}


@router.get("/request-status")
async def check_request_status(room_id: str, participant_name: str):
    res = await db.client.table("join_requests") \
        .select("*") \
        .eq("room_id", room_id) \
        .eq("participant_name", participant_name) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    
    if res.data:
        return {
            "id": res.data[0]['id'],
            "status": res.data[0]['status'],
            "liveness_status": res.data[0].get('liveness_status', 'PENDING')
        }
    return {"status": "NOT_FOUND"}


@router.delete("/room/{room_name}")
async def end_room(room_name: str):
    """Force-terminate a LiveKit room."""
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://").replace("ws://", "http://")

    if not api_key or not api_secret or not livekit_url:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured.")

    if not DeleteRoomRequest:
        raise HTTPException(status_code=500, detail="LiveKit API SDK not installed.")

    try:
        async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
            await lk_api.room.delete_room(DeleteRoomRequest(room=room_name))
        return {"deleted": True, "room": room_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete room: {str(e)}")
