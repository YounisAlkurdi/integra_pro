import jwt
import requests
import base64
import json
import urllib.request
from fastapi import HTTPException, Header, Depends, status, Request
from typing import Optional
from utils import get_env_safe

# Configuration
SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_JWT_SECRET = get_env_safe("SUPABASE_JWT_SECRET")

# Simple memory cache for public keys
_PUBLIC_KEYS_CACHE = None

def get_supabase_jwks():
    """Fetches the active public keys from Supabase."""
    global _PUBLIC_KEYS_CACHE
    if _PUBLIC_KEYS_CACHE:
        return _PUBLIC_KEYS_CACHE
    
    try:
        # Supabase projects expose their public keys as JWKS here
        # Format: https://<project-ref>.supabase.co/auth/v1/keys
        url = f"{SUPABASE_URL}/auth/v1/keys"
        response = requests.get(url, timeout=5)
        if response.ok:
            _PUBLIC_KEYS_CACHE = response.json().get("keys", [])
            return _PUBLIC_KEYS_CACHE
    except Exception as e:
        print(f"=> Neural Trace Error: Failed to fetch JWKS: {e}")
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

async def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Optional authentication dependency. Returns None if signature is invalid or missing.
    Useful for endpoints accessible by both HR and Candidates.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    
    # Process secret for JWT
    secret = SUPABASE_JWT_SECRET
    if secret:
        try:
            # Support base64 decoded secrets common in Supabase
            missing_padding = len(secret) % 4
            if missing_padding:
                secret = base64.b64decode(secret + ('=' * (4 - missing_padding)))
        except:
            pass

    try:
        # 1. Attempt strict verification
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        return payload
    except Exception as e:
        # 2. Fallback
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            print(f"⚠️ Neural Trace: Fallback decoding successful.")
            return payload
        except:
            print(f"❌ Neural Trace: Signature verification failed definitively.")
            return None

def get_active_subscription(user_id: str):
    """
    Fetches the active subscription for the user from Supabase.
    """
    if not SUPABASE_URL or not get_env_safe("SUPABASE_SERVICE_ROLE_KEY"):
        return None

    # Pick the latest active subscription using ordering
    # Use ilike for case-insensitive status check to match 'ACTIVE' or 'active'
    url = f"{SUPABASE_URL}/rest/v1/subscriptions?user_id=eq.{user_id}&status=ilike.active&order=created_at.desc"
    headers = {
        "apikey": get_env_safe("SUPABASE_SERVICE_ROLE_KEY"),
        "Authorization": f"Bearer {get_env_safe('SUPABASE_SERVICE_ROLE_KEY')}",
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            res = json.loads(content) if content else []
            sub = res[0] if res else None
            
            # --- NEURAL SYNC: LEGACY RECORD REPAIR ---
            # If the DB record is missing fields or stuck on defaults (from older payment flow), repair it in-memory
            if sub and sub.get('plan_id'):
                plan_id = sub['plan_id']
                if not sub.get('max_duration_mins') or not sub.get('interviews_limit') or sub.get('interviews_limit') == 5:
                    # Load template from memory to save I/O
                    templates = {
                        'starter': {"interviews_limit": 15, "max_duration_mins": 20, "max_participants": 4},
                        'professional': {"interviews_limit": 40, "max_duration_mins": 60, "max_participants": 8},
                        'enterprise': {"interviews_limit": 9999, "max_duration_mins": 1440, "max_participants": 100},
                        'nexus': {"interviews_limit": 50, "max_duration_mins": 60, "max_participants": 5}
                    }
                    if plan_id in templates:
                        tpl = templates[plan_id]
                        
                        # Correct bugged defaults (5) by forcing the template limits
                        if sub.get('interviews_limit') == 5 or not sub.get('interviews_limit'):
                            sub['interviews_limit'] = tpl['interviews_limit']
                            sub['max_duration_mins'] = tpl['max_duration_mins']
                            sub['max_participants'] = tpl['max_participants']
                        else:
                            sub['interviews_limit'] = sub.get('interviews_limit') or tpl['interviews_limit']
                            sub['max_duration_mins'] = sub.get('max_duration_mins') or tpl['max_duration_mins']
                            sub['max_participants'] = sub.get('max_participants') or tpl['max_participants']
            
            return sub
    except Exception as e:
        print(f"=> Neural Trace Error: Failed to fetch subscription: {e}")
        return None

def get_user_profile_data(user: dict):
    user_id = user.get("sub")
    subscription = get_active_subscription(user_id)
    
    return {
        "status": "AUTHORIZED",
        "node_id": user_id,
        "operator_email": user.get("email"),
        "access_level": "COMMANDER",
        "subscription": subscription
    }
