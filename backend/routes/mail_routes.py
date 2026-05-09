from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.mailer import send_interview_invitation

router = APIRouter(prefix="/api", tags=["Mail"])

class EmailRequest(BaseModel):
    candidate_name: str
    candidate_email: str
    scheduled_at: str
    room_link: str

import asyncio

@router.post("/send-invitation")
async def send_invitation(data: EmailRequest, user: dict = Depends(get_current_user)):
    """Automated Email Invitation via Gmail SMTP (Delegated to mailer.py)."""
    try:
        # Wrap the synchronous SMTP call in a thread to keep the server non-blocking
        email = await asyncio.to_thread(
            send_interview_invitation,
            candidate_name=data.candidate_name,
            candidate_email=data.candidate_email,
            scheduled_at=data.scheduled_at,
            room_link=data.room_link
        )
        return {"status": "EMAIL_SENT", "id": email["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
