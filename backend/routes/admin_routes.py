from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.auth import get_current_user, get_user_profile_data
from backend.services.database_service import db

router = APIRouter(prefix="/api/admin", tags=["Admin"])

class OrganizationCreateRequest(BaseModel):
    name: str
    subscription_tier: Optional[str] = "FREE"

class UserRoleUpdateRequest(BaseModel):
    role: str
    org_id: Optional[str] = None

async def verify_admin(user: dict = Depends(get_current_user)):
    """Security check to ensure only Super Admins can access these routes."""
    profile = await get_user_profile_data(user)
    if profile.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Superuser Access Denied")
    return profile

@router.get("/organizations")
async def list_organizations(admin: dict = Depends(verify_admin)):
    """Lists all organizations in the platform."""
    try:
        res = await db.client.table("organizations").select("*").execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/organizations")
async def create_organization(req: OrganizationCreateRequest, admin: dict = Depends(verify_admin)):
    """Creates a new enterprise organization."""
    try:
        res = await db.client.table("organizations").insert({
            "name": req.name
        }).execute()
        return {"status": "SUCCESS", "org": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def list_all_users(admin: dict = Depends(verify_admin)):
    """Lists every registered user and their associated organization/role."""
    try:
        # Join access_registry with profiles (if profiles exists) or just return registry
        res = await db.client.table("access_registry").select("*").execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/users/{user_id}/access")
async def update_user_access(user_id: str, req: UserRoleUpdateRequest, admin: dict = Depends(verify_admin)):
    """Updates a user's role and organization association."""
    try:
        update_data = {"role": req.role}
        if req.org_id:
            update_data["org_id"] = req.org_id
            
        registry_res = await db.client.table("access_registry").select("id").eq("user_id", user_id).execute()
        if registry_res.data:
            res = await db.client.table("access_registry") \
                .update(update_data) \
                .eq("user_id", user_id) \
                .execute()
        else:
            insert_data = {"user_id": user_id, "role": req.role}
            if req.org_id:
                insert_data["org_id"] = req.org_id
            res = await db.client.table("access_registry").insert(insert_data).execute()
            
        return {"status": "SUCCESS", "updated": res.data[0] if res.data else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
