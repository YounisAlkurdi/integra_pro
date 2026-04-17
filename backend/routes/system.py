from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Optional
import datetime
from ..core.auth import get_current_user
from ..core.supabase_client import supabase
from ..services.audit_logger import capture_event
from ..core.cache import integra_cache

router = APIRouter(prefix="/system", tags=["System Management"])

@router.post("/reboot")
async def system_reboot(request: Request, user: dict = Depends(get_current_user)):
    """
    Simulates a system reboot and logs the event.
    """
    user_id = user["sub"]
    
    # Audit the event
    capture_event(
        user_id=user_id,
        action="SYSTEM_REBOOT",
        resource="CORE_ENGINE",
        details={"status": "INITIATED", "timestamp": datetime.datetime.now().isoformat()},
        severity="WARNING",
        ip=request.client.host,
        ua=request.headers.get("user-agent", "unknown")
    )
    
    return {"status": "SUCCESS", "message": "System reboot sequence initiated."}

@router.post("/prune")
async def system_prune(request: Request, user: dict = Depends(get_current_user)):
    """
    Prunes stale audit logs older than 30 days.
    """
    user_id = user["sub"]
    
    # Calculate cutoff date (30 days ago)
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    
    try:
        # Delete logs from Supabase
        # Note: Supabase REST API delete uses query params for filtering
        path = f"audit_logs?created_at=lt.{cutoff}"
        deleted_count = await supabase.request("DELETE", path)
        
        # Audit the event
        capture_event(
            user_id=user_id,
            action="PRUNE_LOGS",
            resource="AUDIT_TABLE",
            details={"cutoff": cutoff, "status": "COMPLETED"},
            severity="INFO",
            ip=request.client.host,
            ua=request.headers.get("user-agent", "unknown")
        )
        
        return {"status": "SUCCESS", "message": f"Audit logs older than {cutoff} have been pruned."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prune failed: {str(e)}")

@router.post("/lockdown")
async def system_lockdown(request: Request, user: dict = Depends(get_current_user)):
    """
    Toggles the system-wide emergency lockdown state.
    """
    user_id = user["sub"]
    
    # Get current state
    current_lockdown = integra_cache.get("system:lockdown") or False
    new_state = not current_lockdown
    
    # Set new state
    integra_cache.set("system:lockdown", new_state, ttl=86400) # 24h lockdown by default if not cleared
    
    # Audit the event
    capture_event(
        user_id=user_id,
        action="SYSTEM_LOCKDOWN",
        resource="GLOBAL_STATE",
        details={"locked": new_state, "mode": "EMERGENCY" if new_state else "RESTORED"},
        severity="CRITICAL" if new_state else "WARNING",
        ip=request.client.host,
        ua=request.headers.get("user-agent", "unknown")
    )
    
    return {
        "status": "SUCCESS", 
        "locked": new_state, 
        "message": "Emergency lockdown enabled." if new_state else "System access restored."
    }

@router.get("/status")
async def system_status(user: dict = Depends(get_current_user)):
    """
    Returns the current system security status.
    """
    is_locked = integra_cache.get("system:lockdown") or False
    
    return {
        "status": "HEALTHY",
        "lockdown": is_locked,
        "security_level": "ELEVATED" if is_locked else "STANDARD"
    }

@router.get("/audit-summary")
async def audit_summary(user: dict = Depends(get_current_user)):
    """
    Returns the 5 most recent security events for the dashboard.
    """
    user_id = user["sub"]
    
    # Fetch from Supabase
    logs = await supabase.get(
        "audit_logs", 
        f"user_id=eq.{user_id}&order=created_at.desc&limit=5",
        cache_ttl=30
    )
    
    return logs
