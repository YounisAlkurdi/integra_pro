import os
import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
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
    try:
        from livekit.api import AccessToken, VideoGrants
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"LiveKit SDK Error: {str(e)}. Run: pip install livekit-api",
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

    # --- Schedule Validation ---
    from nodes import get_active_streams
    all_nodes = get_active_streams()
    node = next((n for n in all_nodes if n['room_id'] == req.roomName), None)
    
    if node and node.get('scheduled_at'):
        try:
            sched_str = node['scheduled_at'].replace("Z", "+00:00")
            
            if len(sched_str) == 16:
                sched_str += ":00"
                
            scheduled_time = datetime.datetime.fromisoformat(sched_str)
            
            # Make aware if naive (assume +03:00 for local dev based on metadata)
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
                
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Allow joining 5 minutes before scheduled time
            buffer = datetime.timedelta(minutes=5)
            
            if scheduled_time > (now + buffer):
                wait_duration = scheduled_time - now
                total_seconds = wait_duration.total_seconds()
                
                minutes = int(total_seconds // 60)
                
                # Bilingual high-tech error message
                msg_ar = f"الدخول متاح قبل 5 دقائق من الموعد. يرجى الانتظار {minutes} دقيقة."
                msg_en = f"Access allowed 5m before start. Please wait {minutes} minutes."
                full_msg = f"{msg_ar} | {msg_en}"
                
                raise HTTPException(
                    status_code=403,
                    detail=full_msg,
                )
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            print(f"[LiveKit] Schedule parsing error: {e}")
            pass

    # --- Generate token ---
    try:
        normalized_role = req.role.lower()
        token_req = TokenRequest(
            roomName=req.roomName,
            participantName=req.participantName,
            role=normalized_role,
        )
        token = _build_token(api_key, api_secret, token_req)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_out = traceback.format_exc()
        with open("livekit_error.txt", "w") as f:
            f.write(err_out)
        raise HTTPException(
            status_code=500,
            detail="Token generation failed. See livekit_error.txt",
        )

    return {
        "token":           token,              # JWT the frontend uses to connect
        "url":             livekit_url,        # wss:// address (public, not a secret)
        "roomName":        req.roomName,
        "participantName": req.participantName,
        "role":            normalized_role,
        "ttl":             TOKEN_TTL_SEC,      # inform frontend of expiry
    }


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

    try:
        from livekit.api import LiveKitAPI, DeleteRoomRequest
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
