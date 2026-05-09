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
    manager_id = profile.get("node_id")
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
