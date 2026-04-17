"""
Audit Bridge — Proxy to Unified Audit Logger
"""
from backend.services.audit_logger import log_event

async def log_audit_event(
    user_id: str, 
    action: str, 
    target_resource: str, 
    details: dict, 
    severity: str = "INFO",
    ip_address: str = "unknown", 
    user_agent: str = "unknown"
):
    return await log_event(
        user_id=user_id,
        action=action,
        target_resource=target_resource,
        details=details,
        severity=severity,
        ip_address=ip_address,
        user_agent=user_agent
    )
