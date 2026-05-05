import jwt
import json
import os
import base64
from fastapi import HTTPException, Depends, status, Request
from typing import Optional
from .utils import get_env_safe
from .services.database_service import db

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_JWT_SECRET = get_env_safe("SUPABASE_JWT_SECRET")

# Modern Supabase uses ES256 (Asymmetric) — JWKS is the canonical approach
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = jwt.PyJWKClient(JWKS_URL)


# ─────────────────────────────────────────────
# PLAN LIMITS — Single Source of Truth
# ─────────────────────────────────────────────
_PLAN_LIMITS_CACHE: dict = {}

def _load_plan_limits() -> dict:
    """Load plan limit definitions from pricing.json (the canonical source)."""
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        pricing_path = os.path.join(base_path, "data", "pricing.json")
        with open(pricing_path, "r") as f:
            data = json.load(f)
        plans = data.get("pricing_data", {}).get("plans", [])
        return {p["id"]: p.get("limits", {}) for p in plans}
    except Exception as e:
        print(f"=> WARN: Could not load plan limits from pricing.json: {e}")
        return {}

def get_plan_limits(plan_id: str) -> dict:
    """Returns canonical limits for a plan from pricing.json. Reloads cache if empty."""
    global _PLAN_LIMITS_CACHE
    if not _PLAN_LIMITS_CACHE:
        _PLAN_LIMITS_CACHE = _load_plan_limits()
    return _PLAN_LIMITS_CACHE.get(plan_id, {
        "interviews_per_month": 5,
        "max_duration_mins": 10,
        "max_participants": 2
    })


# ─────────────────────────────────────────────
# Token Verification
# ─────────────────────────────────────────────
async def verify_token(token: str) -> Optional[dict]:
    """
    Core token verification. Supports ES256 (Supabase Modern JWKS) and HS256 (Legacy).
    """
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        kid = header.get("kid")

        # 1. Asymmetric: ES256 via JWKS
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
                # Fall through to HS256 as a last resort

        # 2. Symmetric: HS256
        secret = SUPABASE_JWT_SECRET.strip() if SUPABASE_JWT_SECRET else None
        if secret:
            potential_secrets = []
            for decoder in [base64.b64decode, base64.urlsafe_b64decode]:
                try:
                    missing_padding = len(secret) % 4
                    padded = secret + ("=" * (4 - missing_padding)) if missing_padding else secret
                    potential_secrets.append(decoder(padded))
                except Exception:
                    pass
            potential_secrets.append(secret.encode("utf-8"))

            for s in potential_secrets:
                try:
                    payload = jwt.decode(token, s, algorithms=["HS256"], options={"verify_aud": False})
                    return payload
                except jwt.InvalidSignatureError:
                    continue
                except Exception:
                    continue

        print(f"❌ Neural Trace: Signature verification failed — alg={alg}, kid={kid}")
        return None

    except jwt.ExpiredSignatureError:
        print("❌ Neural Trace: Token expired.")
        return None
    except Exception as e:
        print(f"❌ Neural Trace: Authentication Error: {e}")
        return None


async def get_current_user_optional(request: Request) -> Optional[dict]:
    """Optional auth dependency — returns None if missing or invalid."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    return await verify_token(token)


async def get_current_user(request: Request):
    """Mandatory auth dependency — raises 401 if token is missing or invalid."""
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neural Signature Not Found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ─────────────────────────────────────────────
# Subscription Logic
# ─────────────────────────────────────────────
async def get_active_subscription(user_id: str):
    """
    Fetches the active subscription from the database.

    IMPORTANT: payments.py writes status as "ACTIVE" (uppercase).
    This query must match that exact casing.
    """
    try:
        res = await db.select(
            table="subscriptions",
            filters={"user_id": user_id, "status": "ACTIVE"},
            order="created_at",
            desc=True,
            limit=1
        )
        sub = res[0] if res else None

        # Force inject the current limits from pricing.json as the authoritative source
        if sub and sub.get("plan_id"):
            plan_id = sub["plan_id"]
            limits = get_plan_limits(plan_id)
            if limits:
                sub["interviews_limit"] = limits.get("interviews_per_month", sub.get("interviews_limit", 5))
                sub["max_duration_mins"] = limits.get("max_duration_mins", sub.get("max_duration_mins", 10))
                sub["max_participants"] = limits.get("max_participants", sub.get("max_participants", 2))

        return sub

    except Exception as e:
        print(f"=> Neural Trace Error: Failed to fetch subscription: {e}")
        return None


# ─────────────────────────────────────────────
# User Profile
# ─────────────────────────────────────────────
async def get_user_profile_data(user: dict):
    """Assembles the full user profile with live subscription data."""
    user_id = user.get("sub")
    subscription = await get_active_subscription(user_id)

    return {
        "status": "AUTHORIZED",
        "node_id": user_id,
        "operator_email": user.get("email"),
        "access_level": "COMMANDER",
        "subscription": subscription
    }
