from typing import List, Optional
from pydantic import BaseModel
from ..supabase_client import supabase

class ChatLogEntry(BaseModel):
    node_id: str
    sender: str
    message: str

async def save_chat_log(log: ChatLogEntry, user_id: str):
    """
    Saves a single transcript segment to the database.
    """
    body = {
        "node_id": log.node_id,
        "sender": log.sender,
        "message": log.message,
        "user_id": user_id
    }
    return await supabase.post("chat_logs", body)

async def get_node_chat_logs(node_id: str, user_id: str):
    """
    Retrieves all transcript segments for a particular interview.
    """
    query = f"node_id=eq.{node_id}&user_id=eq.{user_id}&order=timestamp.asc"
    return await supabase.get("chat_logs", query)
