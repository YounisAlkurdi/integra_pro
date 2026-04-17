"""
Audit Logger — Integra SaaS
Tracks critical management operations for security and compliance.
"""

import json
import asyncio
import datetime
from typing import Optional
from backend.core.supabase_client import supabase

async def log_event(
    user_id: str, 
    action: str, 
    target_resource: str, 
    resource_id: Optional[str] = None, 
    details: Optional[dict] = None,
    status: str = "SUCCESS",
    severity: str = "INFO",
    ip_address: str = "unknown",
    user_agent: str = "unknown"
):
    """
    Logs a security or management event to Supabase.
    """
    try:
        await supabase.post("audit_logs", {
            "user_id": user_id,
            "action": action,
            "target_resource": target_resource,
            "resource_id": resource_id,
            "details": details or {},
            "status": status,
            "severity": severity,
            "ip_address": ip_address,
            "user_agent": user_agent
        })
    except Exception as e:
        print(f"CRITICAL: Audit Log Failure: {e}")

def capture_event(
    user_id: str, 
    action: str, 
    resource: str, 
    resource_id: Optional[str] = None, 
    details: Optional[dict] = None, 
    severity: str = "INFO",
    ip: str = "unknown", 
    ua: str = "unknown"
):
    """Fire-and-forget wrapper for log_event."""
    asyncio.create_task(log_event(
        user_id, action, resource, resource_id, details, 
        severity=severity, ip_address=ip, user_agent=ua
    ))
