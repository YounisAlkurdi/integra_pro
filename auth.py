import jwt
from fastapi import HTTPException, Header, Depends
from typing import Optional
from utils import get_env_safe

# Supabase Auth Configuration
SUPABASE_JWT_SECRET = get_env_safe("SUPABASE_JWT_SECRET")

async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Neural Verification Protocol (JWT Auth).
    Decodes and validates the Supabase access token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Identity Signal Missing: Authentication required."
        )
    
    token = authorization.split(" ")[1]
    try:
        # Supabase uses HS256 for JWT
        payload = jwt.decode(
            token, 
            SUPABASE_JWT_SECRET, 
            algorithms=["HS256"], 
            audience="authenticated"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail="Signal Expired: Re-authenticate to access node."
        )
    except Exception:
        raise HTTPException(
            status_code=403, 
            detail="Security Violation: Invalid identity signature."
        )

def get_user_profile_data(user: dict):
    """
    Extracts operator metadata from verified payload.
    """
    return {
        "status": "AUTHORIZED",
        "node_id": user.get("sub"),
        "operator_email": user.get("email"),
        "access_level": "COMMANDER"
    }
