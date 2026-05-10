import uuid
import mimetypes
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from backend.services.database_service import db

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
        # Sanitization: If video_path is a full URL, extract the relative path
        # Pattern: .../public/verification_videos/ROOM_ID/FILE.mp4
        if "verification_videos/" in video_path:
            video_path = video_path.split("verification_videos/")[-1]

        # Security: Extract room_id from path (format: "room-uuid/filename.mp4")
        # Now video_path is guaranteed to be "room-uuid/filename.mp4"
        room_id_from_path = video_path.split('/')[0]

        # Validate that room_id_from_path is a valid UUID to avoid 22P02 error
        try:
            target_id = uuid.UUID(room_id_from_path)
        except ValueError:
            print(f"❌ [INTEGRA_SECURITY] Invalid ID format in path: {room_id_from_path}")
            return None

        # 1. Try to find directly as a Room ID
        ownership_check = await db.select(
            table="nodes",
            filters={"room_id": room_id_from_path, "user_id": user_id},
            limit=1
        )
        
        # 2. If not found, it might be a Join Request ID (Verification Video)
        if not ownership_check:
            jr_check = await db.select(
                table="join_requests",
                filters={"id": room_id_from_path},
                limit=1
            )
            if jr_check:
                actual_room_id = jr_check[0].get("room_id")
                # Now check ownership of the parent room
                ownership_check = await db.select(
                    table="nodes",
                    filters={"room_id": actual_room_id, "user_id": user_id},
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

async def get_organization_stats(org_id: str):
    """Fetches aggregate telemetry for the entire organization via the manager view."""
    if not db.client or not org_id: 
        return {"total_interviews": 0, "active_recruiters": 0, "completed_interviews": 0, "avg_candidate_score": 0, "org_name": "Unknown"}
    
    try:
        # 1. Get Organization Name
        org_res = await db.client.table("organizations").select("name").eq("id", org_id).execute()
        org_name = org_res.data[0]["name"] if org_res.data else "Enterprise Node"

        # 2. Get Recruiters
        members = await db.client.table("access_registry").select("user_id").eq("org_id", org_id).execute()
        member_ids = [m["user_id"] for m in members.data] if members.data else []
        active_recruiters = len(member_ids)

        # 3. Aggregate Stats
        total_interviews = 0
        completed_interviews = 0
        for uid in member_ids:
            stats = await get_node_stats(uid)
            total_interviews += stats.get("total", 0)
            completed_interviews += stats.get("completed", 0)

        # 4. Calculate Average Trust Score
        recruiters_data = await get_organization_recruiters(org_id)
        if recruiters_data:
            avg_trust = sum([r["avg_trust_score"] for r in recruiters_data]) / len(recruiters_data)
        else:
            avg_trust = 0

        return {
            "total_interviews": total_interviews,
            "active_recruiters": active_recruiters,
            "completed_interviews": completed_interviews,
            "avg_candidate_score": round(avg_trust),
            "org_name": org_name
        }
    except Exception as e:
        print(f"❌ [INTEGRA_CORE] Failed to fetch organization stats: {e}")
        return {"total_interviews": 0, "active_recruiters": 0, "completed_interviews": 0, "avg_candidate_score": 0, "org_name": "Error"}

async def get_organization_recruiters(org_id: str):
    """Fetches performance metrics for each recruiter within the organization, including their real profiles."""
    if not db.client or not org_id: return []
    
    try:
        # Fetch all members of the organization
        members = await db.client.table("access_registry").select("*").eq("org_id", org_id).execute()
        
        results = []
        for m in members.data:
            try:
                u_id = m["user_id"]
                stats = await get_node_stats(u_id)
                
                # 1. Fetch real profile data
                profile_res = await db.client.table("profiles").select("email, full_name, avatar_url, updated_at").eq("id", u_id).execute()
                profile = profile_res.data[0] if profile_res.data else {}
                
                # 2. Calculate real Trust Score from evaluations
                evals_res = await db.client.table("recruiter_evaluations").select("rating_efficiency, rating_quality").eq("recruiter_id", u_id).execute()
                evals = evals_res.data or []
                
                if evals:
                    total_pts = sum([e["rating_efficiency"] + e["rating_quality"] for e in evals])
                    max_pts = len(evals) * 10
                    trust_score = round((total_pts / max_pts) * 100)
                else:
                    trust_score = None  # No evaluations yet — show as '--' on frontend
                
                # 3. Determine status
                is_active = False
                last_seen = profile.get("updated_at")
                if last_seen:
                    from datetime import datetime, timezone
                    try:
                        last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                        diff = (datetime.now(timezone.utc) - last_seen_dt).total_seconds()
                        if diff < 600: # 10 minutes
                            is_active = True
                    except: pass

                results.append({
                    "user_id": u_id,
                    "role": m.get("role") or "RECRUITER",
                    "full_name": profile.get("full_name") or f"Agent {u_id[:6].upper()}",
                    "email": profile.get("email") or f"operator.{u_id[:4]}@integra.local",
                    "avatar_url": profile.get("avatar_url"),
                    "total_interviews": stats.get("total", 0),
                    "active_interviews": stats.get("active", 0),
                    "completed_interviews": stats.get("completed", 0),
                    "avg_trust_score": trust_score,
                    "is_active": is_active,
                    "last_seen": last_seen
                })
            except Exception as member_err:
                print(f"⚠️ [INTEGRA_CORE] Skipping corrupted recruiter record {m.get('user_id')}: {member_err}")
                continue

        return results
    except Exception as e:
        print(f"❌ [INTEGRA_CORE] Critical failure in organization recruiters fetch: {e}")
        return []

async def get_organization_rooms(org_id: str, manager_user_id: str = None):
    """Fetches rooms created by RECRUITER members of the org, only AFTER they joined.
    
    Rules:
    - Only RECRUITER role members (not MANAGER/ADMIN)
    - Only rooms created after the recruiter's join date (access_registry.created_at)
    - Excludes deleted rooms
    """
    if not db.client or not org_id: return []
    try:
        # 1. Get only RECRUITER members with their join date
        members_res = await db.client.table("access_registry") \
            .select("user_id, role, created_at") \
            .eq("org_id", org_id) \
            .eq("role", "RECRUITER") \
            .execute()
        
        members = members_res.data or []
        
        if not members:
            print(f"🔍 [INTEGRA_MANAGER] No RECRUITER members found in org {org_id}")
            return []
        
        print(f"🔍 [INTEGRA_MANAGER] Found {len(members)} recruiters in org {org_id}")
        
        # 2. For each recruiter, fetch only rooms created AFTER their join date
        all_rooms = []
        profile_cache = {}
        
        for member in members:
            u_id = member["user_id"]
            joined_at = member.get("created_at")  # ISO timestamp of when they joined
            
            # Build query: non-deleted rooms by this recruiter
            query = db.client.table("nodes") \
                .select("*") \
                .eq("user_id", u_id) \
                .eq("is_deleted", False)
            
            # Only include rooms created AFTER the recruiter joined the org
            if joined_at:
                query = query.gte("created_at", joined_at)
            
            rooms_res = await query.order("created_at", desc=True).execute()
            recruiter_rooms = rooms_res.data or []
            
            # Attach creator name
            if u_id not in profile_cache:
                profile_res = await db.client.table("profiles").select("full_name").eq("id", u_id).execute()
                if profile_res.data and profile_res.data[0].get("full_name"):
                    profile_cache[u_id] = profile_res.data[0]["full_name"]
                else:
                    profile_cache[u_id] = "HR Agent"
            
            for room in recruiter_rooms:
                room["creator_name"] = profile_cache[u_id]
            
            all_rooms.extend(recruiter_rooms)
        
        # 3. Sort all rooms by created_at descending
        all_rooms.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        
        print(f"✅ [INTEGRA_MANAGER] Returning {len(all_rooms)} recruiter rooms for org {org_id}")
        return all_rooms
        
    except Exception as e:
        print(f"❌ [INTEGRA_CORE] Failed to fetch organization rooms: {e}")
        return []

