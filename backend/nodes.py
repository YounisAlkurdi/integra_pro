import uuid
import mimetypes
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from .services.database_service import db

class NodeProtocol(BaseModel):
    candidate_name: str
    candidate_email: Optional[str] = None
    position: str
    questions: List[str]
    scheduled_at: str
    room_id: Optional[str] = None
    status: str = "PENDING"
    max_duration_mins: Optional[int] = 10
    max_participants: Optional[int] = 2

async def ensure_bucket_exists(bucket_name: str):
    """
    Tries to create a bucket if it doesn't exist using the async client.
    """
    if not db.client: return
    try:
        await db.client.storage.get_bucket(bucket_name)
    except Exception:
        try:
            await db.client.storage.create_bucket(bucket_name, options={"public": True})
        except Exception as e:
            print(f"Neural Buffer Storage Error: Could not create bucket {bucket_name}: {e}")

async def upload_to_supabase_storage(bucket: str, path: str, file_path: str):
    """
    Uploads a local file to Supabase Storage asynchronously and returns the public URL.
    """
    if not db.client: return None

    await ensure_bucket_exists(bucket)

    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        content_type, _ = mimetypes.guess_type(file_path)
        
        # storage operations are async in the newer sdk versions when using AsyncClient
        await db.client.storage.from_(bucket).upload(
            path=path,
            file=file_data,
            file_options={"content-type": content_type or "application/octet-stream", "upsert": "true"}
        )
        
        return db.client.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        print(f"Storage Upload Failed: {e}")
        return None

async def create_neural_node(node: NodeProtocol, user_id: str):
    """Initializes a permanent control node in the database asynchronously."""
    room_id = str(uuid.uuid4())
    data = {**node.dict(), "user_id": user_id, "room_id": room_id}
    
    result = await db.insert("nodes", data)
    return result if result else data

async def get_active_streams(user_id: str = None):
    """Returns nodes for a user that are NOT marked as deleted asynchronously."""
    if not user_id: return []
    
    return await db.select(
        table="nodes",
        filters={"user_id": user_id, "is_deleted": False},
        order="created_at",
        desc=True
    )

async def get_node_by_room_id(room_id: str):
    """Fetches a specific node by its room_id asynchronously."""
    res = await db.select(table="nodes", filters={"room_id": room_id}, limit=1)
    return res[0] if res else None

async def delete_node(room_id: str):
    """Marks node as archived and COMPLETED asynchronously."""
    res = await db.update(
        table="nodes",
        data={"is_deleted": True, "status": "COMPLETED"},
        filters={"room_id": room_id}
    )
    return len(res) > 0

async def get_node_stats(user_id: str = None):
    """Calculates usage telemetry since the last payment asynchronously."""
    if not user_id:
        return {"total": 0, "active": 0, "completed": 0, "threats": 0}
    
    try:
        # 1. Get Latest Payment
        invoice_resp = await db.select(
            table="invoices",
            filters={"user_id": user_id, "status": "PAID"},
            order="created_at",
            desc=True,
            limit=1
        )
        
        last_payment_date = invoice_resp[0].get('created_at') if invoice_resp else None
        
        # 2. Query Nodes (Manual filter for date to keep DatabaseService simple)
        if not db.client: return {"total": 0, "active": 0, "completed": 0, "threats": 0}
        
        query = db.client.table("nodes").select("status,is_deleted,created_at").eq("user_id", user_id)
        if last_payment_date:
            query = query.gte("created_at", last_payment_date)
        
        node_resp = await query.execute()
        all_nodes = node_resp.data
        
        total_consumed = len(all_nodes)
        active_now = [n for n in all_nodes if not n.get('is_deleted')]
        
        return {
            "total": total_consumed, 
            "active_view": len(active_now),
            "active": sum(1 for n in active_now if n.get('status') == 'PENDING'),
            "completed": sum(1 for n in active_now if n.get('status') == 'COMPLETED'),
            "threats": 0 
        }
    except Exception as e:
        print(f"Failed to calculate node stats: {e}")
        return {"total": 0, "active": 0, "completed": 0, "threats": 0}
