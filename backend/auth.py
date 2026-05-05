import jwt
import base64
import httpx
from fastapi import HTTPException, Header, Depends, status, Request
from typing import Optional
from .utils import get_env_safe
from .services.database_service import db

# Configuration
SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_JWT_SECRET = get_env_safe("SUPABASE_JWT_SECRET")

# Modern Supabase uses ES256 (Asymmetric) - JWKS is the best way to handle this
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = jwt.PyJWKClient(JWKS_URL)

async def get_supabase_jwks():
    """Fetches the active public keys from Supabase asynchronously."""
    # Note: jwks_client handles internal caching
    return []

async def get_current_user(request: Request):
    """
    Mandatory authentication dependency.
    """
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neural Signature Not Found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def verify_token(token: str) -> Optional[dict]:
    """
    Core token verification logic. Supports ES256 (Supabase Modern) and HS256 (Legacy).
    """
    try:
        # 1. Peek at the header to decide which algorithm/key to use
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        kid = header.get("kid")
        
        # 2. Asymmetric Verification (Modern ES256 / JWKS)
        if alg == "ES256":
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token, 
                    signing_key.key, 
                    algorithms=["ES256"], 
                    options={"verify_aud": False}
                )
                return payload
            except Exception as e:
                print(f"❌ Neural Trace: ES256 Verification Failed: {e}")
                # Fallback to HS256 just in case
        
        # 3. Symmetric Verification (Legacy HS256)
        secret = SUPABASE_JWT_SECRET.strip() if SUPABASE_JWT_SECRET else None
        if secret:
            potential_secrets = []
            
            # Base64 decoded versions
            for decoder in [base64.b64decode, base64.urlsafe_b64decode]:
                try:
                    missing_padding = len(secret) % 4
                    s_to_decode = secret + ('=' * (4 - missing_padding)) if missing_padding else secret
                    potential_secrets.append(decoder(s_to_decode))
                except Exception:
                    pass
            
            # Raw string version
            potential_secrets.append(secret.encode('utf-8'))

            for s in potential_secrets:
                try:
                    payload = jwt.decode(token, s, algorithms=["HS256"], options={"verify_aud": False})
                    return payload
                except jwt.InvalidSignatureError:
                    continue
                except Exception:
                    continue

        print(f"❌ Neural Trace: Invalid token: Signature verification failed for alg={alg}, kid={kid}")
        if secret:
            print(f"💡 Hint: The secret in .env starts with '{secret[:10]}...' and is {len(secret)} chars long.")
        return None

    except jwt.ExpiredSignatureError:
        print("❌ Neural Trace: Signature expired.")
        return None
    except Exception as e:
        print(f"❌ Neural Trace: Authentication Error: {e}")
        return None

async def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Optional authentication dependency. Returns None if signature is invalid or missing.
    Automatically detects algorithm (HS256 vs ES256) and uses appropriate verification.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    return await verify_token(token)

async def get_active_subscription(user_id: str):
    """
    Fetches the active subscription for the user using the Async Database Service.
    """
    try:
        # Pick the latest active subscription
        res = await db.select(
            table="subscriptions",
            filters={"user_id": user_id, "status": "active"},
            order="created_at",
            desc=True,
            limit=1
        )
        
        sub = res[0] if res else None
        
        # --- NEURAL SYNC: LEGACY RECORD REPAIR ---
        if sub and sub.get('plan_id'):
            plan_id = sub['plan_id']
            if not sub.get('max_duration_mins') or not sub.get('interviews_limit') or sub.get('interviews_limit') == 5:
                templates = {
                    'starter': {"interviews_limit": 15, "max_duration_mins": 20, "max_participants": 4},
                    'professional': {"interviews_limit": 40, "max_duration_mins": 60, "max_participants": 8},
                    'enterprise': {"interviews_limit": 9999, "max_duration_mins": 1440, "max_participants": 100},
                    'nexus': {"interviews_limit": 50, "max_duration_mins": 60, "max_participants": 5}
                }
                if plan_id in templates:
                    tpl = templates[plan_id]
                    sub['interviews_limit'] = sub.get('interviews_limit') if sub.get('interviews_limit') not in [5, None] else tpl['interviews_limit']
                    sub['max_duration_mins'] = sub.get('max_duration_mins') or tpl['max_duration_mins']
                    sub['max_participants'] = sub.get('max_participants') or tpl['max_participants']
        
        return sub
    except Exception as e:
        print(f"=> Neural Trace Error: Failed to fetch subscription: {e}")
        return None

async def get_user_profile_data(user: dict):
    """
    Returns user profile with active subscription details.
    """
    user_id = user.get("sub")
    subscription = await get_active_subscription(user_id)
    
    return {
        "status": "AUTHORIZED",
        "node_id": user_id,
        "operator_email": user.get("email"),
        "access_level": "COMMANDER",
        "subscription": subscription
    }
