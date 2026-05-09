from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.auth import get_current_user, get_user_profile_data
from backend.services.database_service import db

router = APIRouter(prefix="/api/user", tags=["Identity"])

class JoinOrgRequest(BaseModel):
    invite_code: str

class CreateOrgRequest(BaseModel):
    name: str

@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Identity Retrieval Node."""
    return await get_user_profile_data(user)

@router.post("/join-org")
async def join_organization(req: JoinOrgRequest, user: dict = Depends(get_current_user)):
    """Links an HR Recruiter to a Manager's organization using an invite code."""
    # Look up the organization by invite_code or id
    try:
        org_res = await db.client.table("organizations") \
            .select("id") \
            .eq("id", req.invite_code) \
            .execute()
        
        # If not found by ID, try finding by a hypothetical invite_code column
        if not org_res.data:
            org_res = await db.client.table("organizations") \
                .select("id") \
                .eq("invite_code", req.invite_code) \
                .execute()

        if not org_res.data:
            raise HTTPException(status_code=404, detail="Invalid Organization Invite Code")
            
        org_id = org_res.data[0]["id"]
        
        # Update user's access registry
        user_id = user["sub"]
        registry_res = await db.client.table("access_registry").select("id").eq("user_id", user_id).execute()
        if registry_res.data:
            await db.client.table("access_registry") \
                .update({"org_id": org_id}) \
                .eq("user_id", user_id) \
                .execute()
        else:
            await db.client.table("access_registry") \
                .insert({"user_id": user_id, "org_id": org_id, "role": "RECRUITER"}) \
                .execute()
            
        return {"status": "SUCCESS", "message": "Joined organization successfully.", "org_id": org_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-org")
async def create_organization(req: CreateOrgRequest, user: dict = Depends(get_current_user)):
    """Self-serve route for users to create a company and become its Manager."""
    try:
        # Create the organization
        res = await db.client.table("organizations").insert({
            "name": req.name
        }).execute()
        
        org_id = res.data[0]["id"]
        user_id = user["sub"]
        
        # Promote user to Manager of this organization
        registry_res = await db.client.table("access_registry").select("id").eq("user_id", user_id).execute()
        if registry_res.data:
            await db.client.table("access_registry") \
                .update({"org_id": org_id, "role": "MANAGER"}) \
                .eq("user_id", user_id) \
                .execute()
        else:
            await db.client.table("access_registry") \
                .insert({"user_id": user_id, "org_id": org_id, "role": "MANAGER"}) \
                .execute()
            
        return {"status": "SUCCESS", "message": "Organization created.", "org": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
