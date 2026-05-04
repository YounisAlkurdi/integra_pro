from fastapi import APIRouter, Depends
from ..auth import get_current_user, get_user_profile_data

router = APIRouter(prefix="/api", tags=["Identity"])

@router.get("/user-profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Identity Retrieval Node."""
    return await get_user_profile_data(user)
