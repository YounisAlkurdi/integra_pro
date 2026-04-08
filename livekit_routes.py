import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ── LiveKit Token Module ─────────────────────────────────────────────────────
# ⚠️  SECURITY:
#     LIVEKIT_API_KEY and LIVEKIT_API_SECRET are read here from .env (via dotenv
#     loaded in main.py). They are NEVER returned to the client — only a
#     short-lived signed JWT token is.
# ────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/livekit", tags=["LiveKit"])

VALID_ROLES = {"hr", "candidate"}


class TokenRequest(BaseModel):
    roomName: str
    participantName: str
    role: str               # "hr" | "candidate"


def _build_token(api_key: str, api_secret: str, req: TokenRequest) -> str:
    """
    LiveKit Token Factory.
    Generates a signed JWT that the frontend uses to join a LiveKit room.
    The token expires in 1 hour and carries the participant's role as metadata.
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
    Response:     { token, url, roomName, participantName, role }
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
    api_key    = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured on the server.",
        )

    # --- Generate token ---
    try:
        req.role = req.role.lower()
        token = _build_token(api_key, api_secret, req)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_out = traceback.format_exc()
        with open("livekit_error.txt", "w") as f:
            f.write(err_out)
        raise HTTPException(
            status_code=500,
            detail=f"Token generation failed. See livekit_error.txt",
        )

    return {
        "token": token,              # JWT the frontend uses to connect
        "url":   livekit_url,        # wss:// address (public, not a secret)
        "roomName":        req.roomName,
        "participantName": req.participantName,
        "role":            req.role,
    }
