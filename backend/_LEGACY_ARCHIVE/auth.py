import jwt
import httpx
import base64
import json
import time
from fastapi import HTTPException, Header, Depends
from typing import Optional
from .utils import get_env_safe, cache
from .supabase_client import supabase

# Configuration
SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_JWT_SECRET = get_env_safe("SUPABASE_JWT_SECRET")

async def get_supabase_jwks():
    """Fetches the active public keys from Supabase with caching."""
    cache_key = "jwks_keys"
    cached_keys = cache.get(cache_key)
    if cached_keys:
        return cached_keys
    
    try:
        url = f"{SUPABASE_URL}/auth/v1/keys"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5)
            if response.status_code == 200:
                keys = response.json().get("keys", [])
                cache.set(cache_key, keys, ttl=3600)
                return keys
    except Exception as e:
        print(f"=> Auth Error: Failed to fetch JWKS: {e}")
    return []

async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Neural Verification Protocol (V3).
    Verifies JWT from Supabase.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Identity Signal Missing.")
    
    token = authorization.split(" ")[1]
    
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        
        if alg.startswith("ES"):
            # Asymmetric (ES256) - Requires JWKS or local public key
            if SUPABASE_JWT_SECRET and "-----BEGIN PUBLIC KEY-----" in SUPABASE_JWT_SECRET:
                return jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["ES256"], options={"verify_aud": False})
            
            # Fallback: In production, we should fetch from JWKS and verify
            # For now, we'll raise an error if not configured
            raise HTTPException(status_code=401, detail="Asymmetric Signal Verification not locally configured.")
        
        else:
            # Symmetric (HS256)
            if not SUPABASE_JWT_SECRET:
                raise HTTPException(status_code=500, detail="Security Protocol Failure: JWT Secret missing.")

            secret = SUPABASE_JWT_SECRET
            try:
                # Handle base64 encoded secrets
                missing_padding = len(secret) % 4
                padded_secret = secret + ('=' * (4 - missing_padding)) if missing_padding else secret
                secret = base64.b64decode(padded_secret)
            except:
                pass 

            return jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Signal Expired.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Identity Verification Failed: {str(e)}")

async def get_active_subscription(user_id: str):
    """Fetches the active subscription for the user with caching."""
    res = await supabase.get("subscriptions", f"user_id=eq.{user_id}&status=ilike.active&order=created_at.desc", use_cache=True, ttl=300)
    sub = res[0] if res else None
    
    if sub and sub.get('plan_id'):
        # Repair logic if data is missing
        plan_id = sub['plan_id']
        templates = {
            'starter': {"interviews_limit": 15, "max_duration_mins": 20, "max_participants": 4},
            'professional': {"interviews_limit": 40, "max_duration_mins": 60, "max_participants": 8},
            'enterprise': {"interviews_limit": 9999, "max_duration_mins": 1440, "max_participants": 100},
            'nexus': {"interviews_limit": 50, "max_duration_mins": 60, "max_participants": 5}
        }
        if plan_id in templates:
            tpl = templates[plan_id]
            sub['interviews_limit'] = sub.get('interviews_limit') or tpl['interviews_limit']
            sub['max_duration_mins'] = sub.get('max_duration_mins') or tpl['max_duration_mins']
            sub['max_participants'] = sub.get('max_participants') or tpl['max_participants']
            
    return sub

async def get_user_profile_data(user: dict):
    user_id = user.get("sub")
    subscription = await get_active_subscription(user_id)
    
    return {
        "status": "AUTHORIZED",
        "node_id": user_id,
        "operator_email": user.get("email"),
        "access_level": "COMMANDER",
        "subscription": subscription
    }
