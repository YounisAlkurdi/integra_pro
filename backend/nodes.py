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
        
        # get_public_url is synchronous (just builds a URL string) — do NOT await
        url = db.client.storage.from_(bucket).get_public_url(path)
        # Supabase SDK may return a coroutine on some versions — guard against it
        if hasattr(url, '__await__'):
            import asyncio
            url = await asyncio.ensure_future(url)
        return url
    except Exception as e:
        print(f"Storage Upload Failed: {e}")
        return None

async def create_neural_node(node: NodeProtocol, user_id: str):
    """Initializes a permanent control node in the database asynchronously."""
    room_id = str(uuid.uuid4())
    # Explicitly set is_deleted: False to ensure immediate visibility in synced views
    data = {**node.dict(), "user_id": user_id, "room_id": room_id, "is_deleted": False}
    
    result = await db.insert("nodes", data)
    return result if result else data

async def get_active_streams(user_id: str = None):
    """Returns nodes for a user that are NOT marked as deleted asynchronously."""
    if not user_id: return []
    
    # Use SQL filtering for maximum performance and reliability
    nodes = await db.select(
        table="nodes",
        filters={"user_id": user_id, "is_deleted": False},
        order="created_at",
        desc=True
    )
    
    print(f"⚡ [INTEGRA_CORE] Fetched {len(nodes)} active streams for user: {user_id}")
    return nodes

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

async def purge_completed_nodes(user_id: str):
    """Marks all COMPLETED nodes as archived for a specific user."""
    if not db.client: return 0
    res = await db.client.table("nodes").update({"is_deleted": True}).eq("user_id", user_id).eq("status", "COMPLETED").eq("is_deleted", False).execute()
    return len(res.data) if res.data else 0

async def get_node_stats(user_id: str = None):
    """Calculates usage telemetry since the last payment and current live/completed counts."""
    if not user_id:
        return {"total": 0, "active": 0, "completed": 0, "threats": 0}
    
    try:
        if not db.client: return {"total": 0, "active": 0, "completed": 0, "threats": 0}
        
        # 1. Get Latest Payment / Billing Cycle Start for Quota
        invoice_resp = await db.select(
            table="invoices",
            filters={"user_id": user_id, "status": "PAID"},
            order="created_at",
            desc=True,
            limit=1
        )
        last_payment_date = invoice_resp[0].get('created_at') if invoice_resp else None
        
        # 2. Fetch ALL nodes for status tracking (Active/Completed)
        all_nodes_resp = await db.client.table("nodes").select("status,is_deleted,created_at").eq("user_id", user_id).execute()
        all_nodes = all_nodes_resp.data or []
        
        # 3. Calculate Global Status Counts (Non-deleted only)
        active_count = sum(1 for n in all_nodes if n.get('status') == 'PENDING' and not n.get('is_deleted'))
        completed_count = sum(1 for n in all_nodes if n.get('status') == 'COMPLETED' and not n.get('is_deleted'))
        
        # 4. Calculate Quota Consumption (Total nodes created in this cycle, including deleted ones)
        if last_payment_date:
            from datetime import datetime
            lp_date = datetime.fromisoformat(last_payment_date.replace('Z', '+00:00'))
            quota_nodes = [n for n in all_nodes if datetime.fromisoformat(n.get('created_at').replace('Z', '+00:00')) >= lp_date]
            total_consumed = len(quota_nodes)
        else:
            total_consumed = len(all_nodes)
        
        return {
            "total": total_consumed, 
            "active": active_count,
            "completed": completed_count,
            "threats": 0 
        }
    except Exception as e:
        print(f"❌ [INTEGRA_CORE] Failed to calculate node stats: {e}")
        return {"total": 0, "active": 0, "completed": 0, "threats": 0}

async def get_signed_video_url(video_path: str, user_id: str):
    """
    Generates a secure Signed URL for a verification video.
    First verifies that the video's room belongs to the requesting user.
    URL expires in 3600 seconds (1 hour).
    """
    if not db.client or not video_path:
        return None

    try:
        # Security: Extract room_id from path (format: "room-uuid/filename.mp4")
        room_id_from_path = video_path.split('/')[0]

        ownership_check = await db.select(
            table="nodes",
            filters={"room_id": room_id_from_path, "user_id": user_id},
            limit=1
        )
        if not ownership_check:
            print(f"🚫 [INTEGRA_SECURITY] Unauthorized video access by user {user_id} for {video_path}")
            return None

        # Generate signed URL — expires in 1 hour
        result = await db.client.storage.from_("verification_videos").create_signed_url(
            path=video_path,
            expires_in=3600
        )
        return result.get("signedURL") or result.get("signed_url")
    except Exception as e:
        print(f"❌ [INTEGRA_CORE] Failed to generate signed URL: {e}")
        return None

async def get_interview_report(room_id: str, user_id: str):
    """
    Fetches the AI-generated interview report for a specific room,
    scoped to the owning user for security.
    """
    if not db.client:
        return None

    try:
        # Verify user owns this room first
        node_check = await db.select(
            table="nodes",
            filters={"room_id": room_id, "user_id": user_id},
            limit=1
        )
        if not node_check:
            return None

        # Fetch AI report data
        result = await db.select(
            table="interview_reports",
            filters={"room_id": room_id},
            limit=1
        )
        return result[0] if result else None
    except Exception as e:
        print(f"❌ [INTEGRA_CORE] Failed to fetch interview report: {e}")
        return None
