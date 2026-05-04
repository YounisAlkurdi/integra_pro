from fastapi import APIRouter, Depends
from typing import Optional
from ..auth import get_current_user, get_current_user_optional
from ..logs import ChatLogEntry, save_chat_log, get_node_chat_logs

router = APIRouter(prefix="/api/logs", tags=["Logs"])

@router.post("")
async def add_chat_log(log: ChatLogEntry, user: Optional[dict] = Depends(get_current_user_optional)):
    """Transcript Recording (Allowed for candidates in active sessions)."""
    user_id = user["sub"] if user else None
    return await save_chat_log(log, user_id=user_id)

@router.get("/{node_id}")
async def fetch_logs(node_id: str, user: dict = Depends(get_current_user)):
    """Transcript Retrieval Protocol."""
    return await get_node_chat_logs(node_id, user_id=user["sub"])
