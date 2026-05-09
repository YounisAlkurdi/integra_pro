from typing import List, Optional
from pydantic import BaseModel
from backend.services.database_service import db

class ChatLogEntry(BaseModel):
    node_id: str
    sender: str
    message: str

async def save_chat_log(log: ChatLogEntry, user_id: Optional[str] = None):
    """
    Saves a single transcript segment asynchronously. 
    If user_id is missing (candidate logging), we derive it from the room owner.
    """
    actual_user_id = user_id
    
    if not actual_user_id:
        # Candidate is logging. Find the owner of this room.
        node_info = await db.select(
            table="nodes",
            columns="user_id",
            filters={"room_id": log.node_id},
            limit=1
        )
        if node_info:
            actual_user_id = node_info[0].get("user_id")
    
    if not actual_user_id:
        print(f"❌ Log Error: No owner found for room {log.node_id}. Log discarded.")
        return []

    body = {
        "room_id": log.node_id, 
        "sender": log.sender,
        "message": log.message,
        "user_id": actual_user_id
    }
    return await db.insert("chat_logs", body)

async def get_node_chat_logs(node_id: str, user_id: str):
    """
    Retrieves all transcript segments for a particular interview asynchronously.
    """
    return await db.select(
        table="chat_logs",
        filters={"room_id": node_id, "user_id": user_id},
        order="created_at",
        desc=False
    )
