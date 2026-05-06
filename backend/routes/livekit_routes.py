import os
import datetime
import json
import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from ..nodes import get_node_by_room_id
from ..services.database_service import db
from ..auth import get_current_user

try:
    from livekit.api import AccessToken, VideoGrants, LiveKitAPI, ListParticipantsRequest, DeleteRoomRequest, ListRoomsRequest
except ImportError:
    AccessToken = VideoGrants = LiveKitAPI = ListParticipantsRequest = DeleteRoomRequest = ListRoomsRequest = None

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
    Enforces subscription limits (duration, participants).
    """
    if not req.roomName.strip() or not req.participantName.strip():
        raise HTTPException(status_code=400, detail="roomName and participantName are required.")

    if req.role.lower() not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    api_key     = os.getenv("LIVEKIT_API_KEY")
    api_secret  = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured.")

    # 1. Fetch Node and Subscription Data
    node = await get_node_by_room_id(req.roomName)
    if not node:
        raise HTTPException(status_code=404, detail="Room not found.")

    if node.get('is_deleted') or node.get('status') == 'COMPLETED':
        raise HTTPException(status_code=410, detail="عذراً، هذا الرابط انتهت صلاحيته. | Session has expired.")

    # Fetch limits from subscription
    owner_id = node.get('user_id')
    sub_res = await db.client.table("subscriptions") \
        .select("max_duration_mins, max_participants") \
        .eq("user_id", owner_id) \
        .eq("status", "ACTIVE") \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    
    sub = sub_res.data[0] if sub_res.data else {}
    max_duration = sub.get('max_duration_mins') or node.get('max_duration_mins', 10)
    max_participants = sub.get('max_participants') or node.get('max_participants', 2)

    # 2. Check Schedule
    if node.get('scheduled_at'):
        try:
            sched_str = node['scheduled_at'].replace("Z", "+00:00")
            if len(sched_str) == 16: sched_str += ":00"
            scheduled_time = datetime.datetime.fromisoformat(sched_str)
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
            now = datetime.datetime.now(datetime.timezone.utc)
            if scheduled_time > (now + datetime.timedelta(minutes=5)):
                raise HTTPException(status_code=403, detail="الدخول متاح قبل 5 دقائق من الموعد. | Access allowed 5m before start.")
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    # 3. Check Participant Limits & Admissions
    if LiveKitAPI:
        try:
            lk_host = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
            async with LiveKitAPI(lk_host, api_key, api_secret) as lk_api:
                p_list = await lk_api.room.list_participants(ListParticipantsRequest(room=req.roomName))
                current_p = len(p_list.participants)
                
                if req.role.lower() == "candidate":
                    candidate_count = sum(1 for p in p_list.participants if p.metadata and '"role":"candidate"' in p.metadata)
                    if candidate_count >= 1:
                        raise HTTPException(status_code=403, detail="عذراً، يوجد مرشح آخر داخل الغرفة بالفعل. | Another candidate is in the room.")

                if current_p >= max_participants:
                    raise HTTPException(status_code=403, detail=f"الغرفة ممتلئة. الحد الأقصى هو {max_participants}. | Room is full.")
        except Exception as e:
            if isinstance(e, HTTPException): raise e

        # Lobby System for Candidates
        if req.role.lower() == "candidate":
            deepfake_required = node.get('deepfake_required', True)
            existing_reqs = await db.client.table("join_requests") \
                .select("*").eq("room_id", req.roomName).eq("participant_name", req.participantName) \
                .order("created_at", desc=True).limit(1).execute()
            
            if existing_reqs.data:
                req_obj = existing_reqs.data[0]
                is_overridden = req_obj.get('is_override', False)
                if req_obj['status'] != 'APPROVED' or (deepfake_required and req_obj.get('liveness_status') != 'VERIFIED' and not is_overridden):
                    return {
                        "status": "AWAITING_APPROVAL",
                        "request_id": req_obj['id'],
                        "liveness_status": req_obj.get('liveness_status', 'PENDING'),
                        "message_ar": "بانتظار موافقة المحاور...",
                        "message_en": "Waiting for HR approval..."
                    }
            else:
                new_req = await db.client.table("join_requests").insert({
                    "room_id": req.roomName, "participant_name": req.participantName, "status": "PENDING"
                }).execute()
                return {
                    "status": "AWAITING_APPROVAL",
                    "request_id": new_req.data[0]['id'],
                    "liveness_status": "PENDING" if deepfake_required else "SKIPPED",
                    "message_ar": "بانتظار موافقة المحاور...",
                    "message_en": "Waiting for HR approval..."
                }

    # 4. Generate Token with Unique Identity
    unique_suffix = uuid.uuid4().hex[:4]
    unique_identity = f"{req.participantName}_{unique_suffix}" if req.role.lower() == "hr" else req.participantName
    
    try:
        normalized_role = req.role.lower()
        dynamic_ttl = 24 * 3600
        
        token = (
            AccessToken(api_key, api_secret)
            .with_identity(unique_identity)
            .with_name(req.participantName)
            .with_ttl(datetime.timedelta(seconds=dynamic_ttl))
            .with_metadata(f'{{"role":"{normalized_role}", "display_name":"{req.participantName}"}}')
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
        raise HTTPException(status_code=500, detail="Token generation failed.")

    return {
        "status":          "GRANTED",
        "token":           token,
        "url":             livekit_url,
        "roomName":        req.roomName,
        "participantName": req.participantName,
        "identity":        unique_identity,
        "role":            normalized_role,
        "max_duration":    max_duration,
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

class ToggleDeepfakeRequest(BaseModel):
    room_id: str
    required: bool

@router.post("/toggle-deepfake")
async def toggle_deepfake_requirement(req: ToggleDeepfakeRequest):
    """HR master switch to enable/disable Deepfake gate for this session."""
    await db.client.table("nodes") \
        .update({"deepfake_required": req.required}) \
        .eq("room_id", req.room_id) \
        .execute()
    return {"status": "UPDATED", "deepfake_required": req.required}


@router.get("/toggle-deepfake")
async def get_deepfake_requirement(room_id: str):
    """Fetch current Gatekeeper AI (Deepfake) gate status for this session."""
    node = await get_node_by_room_id(room_id)
    if not node:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"deepfake_required": node.get("deepfake_required", True)}


@router.post("/decide-request")
async def decide_request(req: DecisionRequest):
    """
    HR decision to allow or block a candidate.
    Must ensure the candidate is VERIFIED before approving.
    """
    # 1. Fetch current liveness status and node settings
    req_res = await db.client.table("join_requests") \
        .select("liveness_status") \
        .eq("room_id", req.room_id) \
        .eq("participant_name", req.participant_name) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Join request not found.")
    
    liveness = req_res.data[0].get("liveness_status", "PENDING")

    # Fetch node settings
    node = await get_node_by_room_id(req.room_id)
    deepfake_required = node.get('deepfake_required', True) if node else True

    # 2. Prevent approval if not verified (ONLY if required and not overridden)
    # SKIPPED is treated as equivalent to VERIFIED (protection was disabled by HR)
    liveness_ok = liveness in ("VERIFIED", "SKIPPED")
    if req.decision.upper() == "APPROVED" and deepfake_required and not liveness_ok and not req.is_override:
        raise HTTPException(
            status_code=403, 
            detail="Security Block: Candidate must be VERIFIED by Gatekeeper before approval can be granted. Use VETO Override if necessary."
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

    if req.decision.upper() == "APPROVED":
        # Mark the session as started if it hasn't been already
        # We can just set started_at = now() for the node.
        # But wait, supabase doesn't easily let us set conditionally if null in one update without raw SQL
        # Let's just fetch it first or simply update it. 
        node = await get_node_by_room_id(req.room_id)
        if node and not node.get('started_at'):
            await db.client.table("nodes") \
                .update({"started_at": "now()"}) \
                .eq("room_id", req.room_id) \
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


class EndVoteRequest(BaseModel):
    room_id: str
    identity: str

@router.post("/vote-end")
async def vote_to_end_session(req: EndVoteRequest, user: dict = Depends(get_current_user)):
    """
    Register a 'Complete' vote from an HR. 
    Session only closes if ALL active HRs have voted to end.
    """
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://").replace("ws://", "http://")

    async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
        # 1. Update this participant's metadata to reflect they want to end
        p_info = await lk_api.room.get_participant(req.room_id, req.identity)
        metadata = json.loads(p_info.metadata or "{}")
        metadata["wants_to_end"] = True
        
        await lk_api.room.update_participant(
            req.room_id, 
            req.identity, 
            metadata=json.dumps(metadata)
        )

        # 2. Check if all OTHER HRs also want to end
        all_p = await lk_api.room.list_participants(ListParticipantsRequest(room=req.room_id))
        
        hr_votes = []
        total_hrs = 0
        
        for p in all_p.participants:
            try:
                m = json.loads(p.metadata or "{}")
                if m.get("role") == "hr":
                    total_hrs += 1
                    if m.get("wants_to_end"):
                        hr_votes.append(True)
                    else:
                        hr_votes.append(False)
            except Exception:
                # Fallback to string matching if JSON fails, but log it
                if '"role":"hr"' in (p.metadata or ""):
                    total_hrs += 1
                    hr_votes.append('"wants_to_end":true' in (p.metadata or ""))

        consensus_reached = all(hr_votes) if total_hrs > 0 else True
        
        if consensus_reached:
            # Finalize Session
            await db.client.table("nodes").update({"status": "COMPLETED"}).eq("room_id", req.room_id).execute()
            await lk_api.room.delete_room(DeleteRoomRequest(room=req.room_id))
            return {"status": "COMPLETED", "consensus": True}
        
        return {
            "status": "VOTED", 
            "consensus": False, 
            "votes": sum(1 for v in hr_votes if v), 
            "total_hrs": total_hrs
        }


@router.post("/complete/{room_id}")
async def complete_session(room_id: str, user: dict = Depends(get_current_user)):
    """Mark session as COMPLETED without hard-deleting the record."""
    await db.client.table("nodes") \
        .update({"status": "COMPLETED"}) \
        .eq("room_id", room_id) \
        .execute()
    
    # Also delete the LiveKit room to kick everyone out
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://").replace("ws://", "http://")
    
    if api_key and api_secret and livekit_url:
        try:
            async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
                await lk_api.room.delete_room(DeleteRoomRequest(room=room_id))
        except Exception as e:
            print(f"[LiveKit] Failed to delete room on completion: {e}")
            
    return {"status": "COMPLETED"}


@router.post("/webhook")
async def livekit_webhook(request: Request):
    """
    LiveKit Webhook Handler.
    Listens for participant events to manage the 5-minute grace period.
    """
    from livekit.api import WebhookReceiver
    
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    receiver = WebhookReceiver(api_key, api_secret)
    
    # 1. Verify and parse event
    body = await request.body()
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
        
    try:
        event = receiver.receive(body.decode("utf-8"), auth_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook signature: {e}")

    # 2. Process Events
    room_name = event.room.name
    
    if event.event == "participant_disconnected":
        # Check if any HRs are still in the room
        metadata = json.loads(event.participant.metadata or "{}")
        if metadata.get("role") == "hr":
            # Check remaining HRs via LiveKit API
            livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://").replace("ws://", "http://")
            async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
                p_list = await lk_api.room.list_participants(ListParticipantsRequest(room=room_name))
                
                hr_count = 0
                for p in p_list.participants:
                    try:
                        m = json.loads(p.metadata or "{}")
                        if m.get("role") == "hr":
                            hr_count += 1
                    except:
                        if '"role":"hr"' in (p.metadata or ""):
                            hr_count += 1
                
                if hr_count == 0:
                    # Update node with last seen timestamp to start 5m grace period
                    # We store it in 'hrs_last_seen_at'
                    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    await db.client.table("nodes") \
                        .update({"hrs_last_seen_at": now_iso}) \
                        .eq("room_id", room_name) \
                        .execute()
    
    elif event.event == "participant_connected":
        metadata = json.loads(event.participant.metadata or "{}")
        if metadata.get("role") == "hr":
            # Reset grace period
            await db.client.table("nodes") \
                .update({"hrs_last_seen_at": None}) \
                .eq("room_id", room_name) \
                .execute()

    return {"status": "processed"}


@router.post("/cleanup-sessions")
async def cleanup_sessions():
    """
    1. Mark sessions where HRs have been gone for > 5m as COMPLETED.
    2. Mark PENDING sessions older than 24h as ARCHIVED/COMPLETED.
    """
    # 1. Grace period cleanup
    # We use raw SQL or filtered update for 'hrs_last_seen_at < now() - 5 minutes'
    await db.client.rpc("archive_empty_rooms").execute()
    
    # 2. Bulk archive old pending
    await db.client.table("nodes") \
        .update({"status": "COMPLETED", "is_deleted": True}) \
        .eq("status", "PENDING") \
        .lt("created_at", (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()) \
        .execute()

    # 3. Finalize: Delete actual LiveKit rooms for all COMPLETED nodes that might still be active
    # This ensures candidates are kicked out even if HRs just vanished
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://").replace("ws://", "http://")
    
    if api_key and api_secret and livekit_url:
        try:
            async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
                # Get rooms marked completed recently or currently
                # For efficiency, we just try to delete all rooms that match our COMPLETED status
                # But LiveKit list_rooms might be better
                rooms_res = await lk_api.room.list_rooms(ListRoomsRequest())
                for r in rooms_res.rooms:
                    # Check if this room exists in our DB as COMPLETED
                    node_res = await db.client.table("nodes").select("status").eq("room_id", r.name).execute()
                    if node_res.data and node_res.data[0]["status"] == "COMPLETED":
                        print(f"[Cleanup] Deleting active LiveKit room for completed session: {r.name}")
                        await lk_api.room.delete_room(DeleteRoomRequest(room=r.name))
        except Exception as e:
            print(f"[Cleanup] Error deleting rooms: {e}")
        
    return {"status": "CLEANED"}


@router.delete("/room/{room_name}")
async def end_room(room_name: str):
    """Force-terminate a LiveKit room and mark node as deleted."""
    from ..nodes import delete_node
    
    # 1. Update DB
    await delete_node(room_name)
    
    # 2. Delete LiveKit Room
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://").replace("ws://", "http://")

    if not api_key or not api_secret or not livekit_url:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured.")

    try:
        async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
            await lk_api.room.delete_room(DeleteRoomRequest(room=room_name))
        return {"deleted": True, "room": room_name}
    except Exception as e:
        # If room already gone, that's fine
        if "not found" in str(e).lower() or "404" in str(e):
            return {"deleted": True, "room": room_name, "note": "Already deleted"}
        raise HTTPException(status_code=500, detail=f"Failed to delete room: {str(e)}")
