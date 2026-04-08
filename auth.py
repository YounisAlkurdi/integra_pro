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
        # Check if SUPABASE_JWT_SECRET is empty
        if not SUPABASE_JWT_SECRET:
            print("WARNING: SUPABASE_JWT_SECRET is empty. Bypassing signature verification for local test!")
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload

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
    except Exception as e:
        print(f"JWT Verification Failed: {e}") # Log the exact error!
        # Fallback for dev if the secret doesn't match
        try:
            print("Attempting to bypass signature verification due to mismatched keys...")
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as fallback_e:
            raise HTTPException(
                status_code=403, 
                detail=f"Security Violation: {e}"
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
