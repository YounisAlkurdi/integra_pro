from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.auth import get_current_user, get_user_profile_data
from backend.nodes import get_organization_stats, get_organization_recruiters, get_node_stats
from backend.services.database_service import db

router = APIRouter(prefix="/api/manager", tags=["Manager"])

class RecruiterEvaluationRequest(BaseModel):
    recruiter_id: str
    rating_efficiency: int # 1-5
    rating_quality: int # 1-5
    notes: Optional[str] = None

async def verify_manager(user: dict = Depends(get_current_user)):
    """Middleware to ensure the user has MANAGER or ADMIN privileges."""
    profile = await get_user_profile_data(user)
    role = profile.get("role")
    if role not in ["MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Executive Access Denied: Manager Role Required")
    return profile

@router.get("/stats")
async def organization_stats(profile: dict = Depends(verify_manager)):
    """Returns aggregate telemetry for the manager's organization."""
    org_id = profile.get("org_id")
    if not org_id:
        return {"total_interviews": 0, "active_recruiters": 0, "completed_interviews": 0, "avg_candidate_score": 0}
    return await get_organization_stats(org_id)

@router.get("/recruiters")
async def organization_recruiters(profile: dict = Depends(verify_manager)):
    """Returns performance breakdown for all recruiters in the organization."""
    org_id = profile.get("org_id")
    if not org_id:
        return []
    return await get_organization_recruiters(org_id)

@router.post("/evaluate")
async def evaluate_recruiter(req: RecruiterEvaluationRequest, profile: dict = Depends(verify_manager)):
    """Allows a manager to submit a formal evaluation for a recruiter in their organization."""
    # تعديل: قراءة الـ ID الصحيح للمدير لحل مشكلة الـ NoneType وطرد السيرفر
    manager_id = profile.get("id") or profile.get("user_id")
    org_id = profile.get("org_id")

    # 1. Verify recruiter belongs to the same org
    recruiter_check = await db.client.table("access_registry") \
        .select("org_id") \
        .eq("user_id", req.recruiter_id) \
        .execute()
    
    if not recruiter_check.data or recruiter_check.data[0]["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Unauthorized: Recruiter not in your organization")

    # 2. Insert evaluation
    try:
        res = await db.client.table("recruiter_evaluations").insert({
            "manager_id": manager_id,  
            "recruiter_id": req.recruiter_id,
            "rating_efficiency": req.rating_efficiency,
            "rating_quality": req.rating_quality,
            "notes": req.notes
        }).execute()
        
        return {"status": "SUCCESS", "evaluation_id": res.data[0]["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/recruiter-reports/{recruiter_id}")
async def get_recruiter_nodes(recruiter_id: str, profile: dict = Depends(verify_manager)):
    """Allows a manager to inspect all interview nodes created by a specific recruiter."""
    org_id = profile.get("org_id")

    # 1. Verify recruiter belongs to the same org
    recruiter_check = await db.client.table("access_registry") \
        .select("org_id") \
        .eq("user_id", recruiter_id) \
        .execute()
    
    if not recruiter_check.data or recruiter_check.data[0]["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Unauthorized: Recruiter not in your organization")

    # 2. Fetch nodes for this recruiter
    try:
        nodes = await db.client.table("nodes") \
            .select("*") \
            .eq("user_id", recruiter_id) \
            .order("created_at", desc=True) \
            .execute()
        return nodes.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/rooms")
async def organization_rooms(profile: dict = Depends(verify_manager)):
    """Returns all interview nodes/rooms created by the organization's recruiters."""
    from backend.nodes import get_organization_rooms
    org_id = profile.get("org_id")
    
    # تعديل: بدلاً من node_id نأخذ المعرف الحقيقي للمدير لمنع انهيار الـ API
    manager_user_id = profile.get("id") or profile.get("user_id") 
    if not org_id:
        return []
    return await get_organization_rooms(org_id, manager_user_id=manager_user_id)
    
@router.delete("/recruiters/{recruiter_id}")
async def remove_recruiter(recruiter_id: str, profile: dict = Depends(verify_manager)):
    """Removes a recruiter from the organization's access registry."""
    org_id = profile.get("org_id")
    
    # Verify the recruiter belongs to this org before removing
    recruiter_check = await db.client.table("access_registry") \
        .select("id, role") \
        .eq("user_id", recruiter_id) \
        .eq("org_id", org_id) \
        .execute()
        
    if not recruiter_check.data:
        raise HTTPException(status_code=404, detail="Recruiter not found in your organization")
        
    # تعديل: استخدام المعرف الصحيح للمدير لحل مشكلة الـ node_id القديمة ومنع حذف نفسه بالخطأ
    current_manager_id = profile.get("id") or profile.get("user_id")
    if recruiter_check.data[0]["role"] == "MANAGER" and recruiter_id == current_manager_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the organization")

    try:
        await db.client.table("access_registry").delete().eq("user_id", recruiter_id).eq("org_id", org_id).execute()
        return {"status": "SUCCESS", "message": "Recruiter removed from organization"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/billing")
async def organization_billing(profile: dict = Depends(verify_manager)):
    """Returns the organization's subscription billing usage and limits."""
    # 1. تعديل: القراءة من الحقل الصحيح لمعرف المستخدم
    user_id = profile.get("id") or profile.get("user_id")
    org_id = profile.get("org_id")
    try:
        sub_res = await db.client.table("subscriptions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
        
        # 2. حماية الكود: لو جدول الاشتراكات فاضي على AWS ما يضرب الـ API ويرجع ديكشنري فارغ
        sub = sub_res.data[0] if sub_res.data else {}
        
        # Aggregate org-wide interviews consumed this cycle
        total_used = 0
        if org_id:
            members_res = await db.client.table("access_registry").select("user_id").eq("org_id", org_id).execute()
            member_ids = [m["user_id"] for m in (members_res.data or [])]
            for uid in member_ids:
                from backend.nodes import get_node_stats
                stats = await get_node_stats(uid)
                # حماية إضافية لو الـ stats رجعت None
                if stats:
                    total_used += stats.get("total", 0)
        
        plan_map = {
            'free': {'label': 'Free Tier', 'price': 0},
            'starter': {'label': 'Starter', 'price': 29},
            'professional': {'label': 'Professional', 'price': 99},
            'nexus': {'label': 'Nexus', 'price': 149},
            'enterprise': {'label': 'Enterprise', 'price': 499},
        }
        plan_id = sub.get("plan_id", "free")
        plan_info = plan_map.get(plan_id.lower(), {'label': plan_id.upper(), 'price': 0})
        
        return {
            "plan_id": plan_id,
            "plan_label": plan_info['label'],
            "plan_price": plan_info['price'],
            "interviews_limit": sub.get("interviews_limit", 10),
            "interviews_used": total_used,
            "max_duration_mins": sub.get("max_duration_mins", 10),
            "max_participants": sub.get("max_participants", 2),
            "next_billing_date": sub.get("next_billing_date", "N/A"),
            "status": sub.get("status", "ACTIVE")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/invite-code")
async def get_invite_code(profile: dict = Depends(verify_manager)):
    """Returns the organization's unique invite code (org_id) for member onboarding."""
    org_id = profile.get("org_id")
    if not org_id:
        raise HTTPException(status_code=404, detail="No organization found for this manager")
    
    try:
        org_res = await db.client.table("organizations").select("id, name").eq("id", org_id).execute()
        if not org_res.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        org = org_res.data[0]
        return {
            "org_id": org["id"],
            "org_name": org.get("name", "Your Organization"),
            "invite_code": org["id"]  # The invite code IS the org_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/audit-logs")
async def get_audit_logs(profile: dict = Depends(verify_manager)):
    """Returns recent security and audit events for the organization."""
    org_id = profile.get("org_id")
    if not org_id:
        return []
    
    try:
        # Get org members first
        members_res = await db.client.table("access_registry").select("user_id").eq("org_id", org_id).execute()
        member_ids = [m["user_id"] for m in (members_res.data or [])]
        
        if not member_ids:
            return []

        # Try fetching from audit_logs if table exists
        try:
            logs_res = await db.client.table("audit_logs") \
                .select("*") \
                .in_("user_id", member_ids) \
                .order("created_at", desc=True) \
                .limit(10) \
                .execute()
            return logs_res.data or []
        except Exception:
            # Table might not exist yet — return empty (no mock data)
            return []
    except Exception as e:
        print(f"❌ [MANAGER] Failed to fetch audit logs: {e}")
        return []