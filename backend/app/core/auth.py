import jwt
import requests
import base64
import json
import time
from fastapi import HTTPException, Header, Depends
from typing import Optional
from ..utils import get_env_safe
from ..supabase_client import supabase

# Configuration
SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_JWT_SECRET = get_env_safe("SUPABASE_JWT_SECRET")

# Advanced Cache Mechanism
_CACHE = {
    "jwks": {"data": None, "timestamp": 0},
    "subscriptions": {} # user_id -> {"data": ..., "timestamp": ...}
}
CACHE_TTL_JWKS = 3600  # 1 hour
CACHE_TTL_SUB = 300    # 5 minutes

def get_supabase_jwks():
    """Fetches the active public keys from Supabase with caching."""
    now = time.time()
    if _CACHE["jwks"]["data"] and (now - _CACHE["jwks"]["timestamp"] < CACHE_TTL_JWKS):
        return _CACHE["jwks"]["data"]
    
    try:
        url = f"{SUPABASE_URL}/auth/v1/keys"
        response = requests.get(url, timeout=5)
        if response.ok:
            keys = response.json().get("keys", [])
            _CACHE["jwks"] = {"data": keys, "timestamp": now}
            return keys
    except Exception as e:
        print(f"=> Neural Trace Error: Failed to fetch JWKS: {e}")
    return _CACHE["jwks"]["data"] or []

async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Neural Verification Protocol (V3).
    Strict verification, no fallbacks to unverified tokens in production.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Identity Signal Missing.")
    
    token = authorization.split(" ")[1]
    
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        
        if alg.startswith("ES"):
            # ASYMMETRIC (ES256)
            keys = get_supabase_jwks()
            if not keys:
                raise HTTPException(status_code=500, detail="Security Protocol Failure: JWKS unavailable.")
            
            if SUPABASE_JWT_SECRET and "-----BEGIN PUBLIC KEY-----" in SUPABASE_JWT_SECRET:
                return jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["ES256"], options={"verify_aud": False})
            
            raise HTTPException(status_code=401, detail="Asymmetric Signal Verification not locally configured.")
        
        else:
            # SYMMETRIC (HS256)
            if not SUPABASE_JWT_SECRET:
                raise HTTPException(status_code=500, detail="Security Protocol Failure: JWT Secret missing.")

            secret = SUPABASE_JWT_SECRET
            try:
                missing_padding = len(secret) % 4
                padded_secret = secret + ('=' * (4 - missing_padding)) if missing_padding else secret
                secret = base64.b64decode(padded_secret)
            except:
                pass 

            return jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Signal Expired.")
    except Exception as e:
        print(f"=> Neural Trace Exception: {e}")
        raise HTTPException(status_code=401, detail=f"Identity Verification Failed: {str(e)}")

def get_active_subscription(user_id: str):
    """
    Fetches the active subscription for the user with caching and repair logic.
    """
    now = time.time()
    if user_id in _CACHE["subscriptions"]:
        entry = _CACHE["subscriptions"][user_id]
        if now - entry["timestamp"] < CACHE_TTL_SUB:
            return entry["data"]

    try:
        # Use sync client for auth middleware compatibility
        res = supabase.get_sync("subscriptions", f"user_id=eq.{user_id}&status=ilike.active&order=created_at.desc")
        sub = res[0] if res else None
        
        if sub and sub.get('plan_id'):
            # --- NEURAL SYNC: LEGACY RECORD REPAIR ---
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
        
        _CACHE["subscriptions"][user_id] = {"data": sub, "timestamp": now}
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
