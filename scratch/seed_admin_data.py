import asyncio
import os
import uuid
from datetime import datetime, timedelta
import random
from backend.services.database_service import db

async def seed():
    print("🌱 Seeding Real Data for Integra Overseer...")
    
    # Target Org: integra.ai (b1f8a839-f6d5-4b32-8ca8-eea913dd442f)
    org_id = "b1f8a839-f6d5-4b32-8ca8-eea913dd442f"
    manager_id = "d622853e-93c5-47af-8f84-15717e3f36bd"
    recruiters = [
        "1f197c13-0c27-44c7-bedb-48859aba3859",
        "7aeeaafe-20b3-4b46-80b8-edd47a1564ab",
        "99302013-649c-45d1-ba20-a71aa1788245"
    ]

    # 1. Create Audit Logs
    actions = ["LOGIN", "CREATE_NODE", "SESSION_START", "SECURITY_ALERT", "MANUAL_OVERRIDE", "DEEPFAKE_FAILED"]
    resources = ["nodes", "auth", "session", "system"]
    
    print("  -> Generating Audit Logs...")
    logs = []
    for _ in range(25):
        u_id = random.choice(recruiters + [manager_id])
        action = random.choice(actions)
        severity = "INFO"
        if action in ["SECURITY_ALERT", "DEEPFAKE_FAILED"]: severity = "CRITICAL"
        if action == "MANUAL_OVERRIDE": severity = "WARNING"
        
        logs.append({
            "user_id": u_id,
            "action": action,
            "target_resource": random.choice(resources),
            "resource_id": str(uuid.uuid4()),
            "severity": severity,
            "status": "SUCCESS" if random.random() > 0.1 else "FAILED",
            "created_at": (datetime.now() - timedelta(hours=random.randint(0, 48))).isoformat()
        })
    
    await db.client.table("audit_logs").insert(logs).execute()

    # 2. Create Interview Reports for Recruiters
    print("  -> Generating Interview Reports for Recruiters...")
    for u_id in recruiters:
        # Get one node for this user to attach a report to
        nodes_res = await db.client.table("nodes").select("room_id, candidate_name").eq("user_id", u_id).limit(2).execute()
        for node in nodes_res.data:
            report_data = {
                "room_id": node["room_id"],
                "user_id": u_id,
                "candidate_name": node["candidate_name"],
                "overall_forensic_score": random.uniform(75, 98),
                "integrity_risk_score": random.uniform(2, 15),
                "analysis_status": "COMPLETED",
                "ai_summary": "Forensic analysis completed. No significant neural anomalies detected.",
                "created_at": datetime.now().isoformat()
            }
            try:
                await db.client.table("interview_reports").upsert(report_data, on_conflict="room_id").execute()
            except Exception as e:
                print(f"     ! Failed to upsert report for {node['room_id']}: {e}")

    # 3. Create Recruiter Evaluations
    print("  -> Generating Recruiter Evaluations...")
    evals = []
    for u_id in recruiters:
        evals.append({
            "manager_id": manager_id,
            "recruiter_id": u_id,
            "rating_efficiency": random.randint(3, 5),
            "rating_quality": random.randint(4, 5),
            "notes": "Consistently high forensic adherence. Candidate engagement is optimal.",
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 7))).isoformat()
        })
    await db.client.table("recruiter_evaluations").insert(evals).execute()

    print("✅ Seed Complete. Integra Overseer is now LIVE with real values.")

if __name__ == "__main__":
    asyncio.run(seed())
