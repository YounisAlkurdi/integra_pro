import os
import json
import uuid
import datetime
import asyncio
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Import project modules
from backend.nodes import get_active_streams, get_node_by_room_id, create_neural_node, get_node_stats, NodeProtocol
from backend.logs import get_node_chat_logs
from backend.mailer import send_interview_invitation
from backend.auth import get_active_subscription
from backend.payments import PRICING_DATA
from backend.services.database_service import DatabaseService

# Load environment
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("Integra Neural Command")

# --- Helper: ID Sanitizer ---
def sanitize_uid(uid: str) -> str:
    if not uid: return ""
    uid = str(uid).strip()
    if uid.startswith('{') and 'user_id' in uid:
        try:
            data = json.loads(uid)
            return data.get('user_id', uid)
        except: pass
    return uid

# --- 0. Metadata: Platform Intelligence ---

@mcp.tool()
async def get_platform_manifest() -> str:
    """
    Returns the Integra Platform Manifest. 
    Provides high-level context about the platform's purpose, forensic capabilities, and architectural limits.
    Use this to introduce the system to the user or to understand the platform's core boundaries.
    """
    return json.dumps({
        "platform": "Integra Forensic Behavioral Engine",
        "version": "4.0.0",
        "tagline": "Beyond Presence — Neural Investigative Intelligence",
        "core_features": [
            "Real-time Neural Node Management",
            "Deepfake Verification (Gatekeeper)",
            "Behavioral Analysis & Iris Tracking",
            "Secure Invitation Protocol",
            "Matrix External Integration (Stripe, Slack, etc.)"
        ],
        "compliance": "GDPR-Forensic-Ready",
        "status": "OPERATIONAL"
    }, indent=2)

# --- 1. Operations: Node Management ---


@mcp.tool()
async def list_active_streams(user_id: str) -> str:
    """Scan Active Data Streams (Search by SUBJECT_IDENTIFICATION). Returns all live nodes for a user."""
    uid = sanitize_uid(user_id)
    sub = await get_active_subscription(uid)
    since = sub.get('created_at') if sub else None
    interviews = await get_active_streams(user_id=uid)
    return json.dumps(interviews, indent=2)

@mcp.tool()
async def establish_secure_link(candidate_name: str, position: str, user_id: str, candidate_email: str = None, scheduled_at: str = None, questions: list[str] = None) -> str:
    """
    INITIALIZE NODE (Establish Secure Link). 
    NOTE: Before calling this, it is HIGHLY RECOMMENDED to call 'sync_neural_quotas' 
    to verify if the user has enough interview slots remaining.
    """
    uid = sanitize_uid(user_id)
    protocol_time = scheduled_at if scheduled_at else datetime.datetime.utcnow().isoformat()
    
    node = NodeProtocol(
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        position=position,
        questions=questions or ["Identify your core strengths.", "Explain your approach to complex system architecture."],
        scheduled_at=protocol_time
    )
    result = await create_neural_node(node, user_id=uid)
    return json.dumps(result, indent=2)

@mcp.tool()
async def transmit_invitation_protocol(candidate_name: str, candidate_email: str, scheduled_at: str, room_id: str) -> str:
    """TRANSMIT INVITATION (Send Email). Dispatches the secure link to the target address."""
    domain = os.getenv("APP_DOMAIN", "https://tist-integra.vercel.app")
    room_link = f"{domain}/integra-session.html?room={room_id}&role=candidate"
    
    # send_interview_invitation is still sync, using to_thread
    email = await asyncio.to_thread(send_interview_invitation, candidate_name, candidate_email, scheduled_at, room_link)
    return json.dumps(email)

# --- 2. System Intelligence & Telemetry ---

@mcp.tool()
async def get_neural_link_status(user_id: str) -> str:
    """Telemetry Node: Total Nodes, Live Sessions, and Memory Capacity."""
    uid = sanitize_uid(user_id)
    stats = await get_node_stats(user_id=uid)
    return json.dumps(stats, indent=2)

@mcp.tool()
async def sync_neural_quotas(user_id: str) -> str:
    """Retrieves the ACTUAL Subscription Plan (Quotas, Limits, and Enforcements) from the LIVE billing system."""
    uid = sanitize_uid(user_id)
    sub = await get_active_subscription(uid)
    
    upgrade_info = {
        "upgrade_links": {
            "professional": "/upgrade?plan=professional",
            "nexus": "/upgrade?plan=nexus"
        },
        "instructions": "If the user is out of slots, suggest they visit the upgrade links above."
    }
    
    if not sub: 
        stats = await get_node_stats(uid)
        return json.dumps({
            "status": "FREE_TIER", 
            "interviews_limit": 5, 
            "usage_count": stats.get('total', 0), 
            **upgrade_info
        })
    
    since = sub.get('created_at')
    stats = await get_node_stats(uid)
    
    return json.dumps({
        "plan_id": sub.get('plan_id'),
        "status": sub.get('status'),
        "interviews_limit": sub.get('interviews_limit'),
        "usage_count": stats.get('total', 0),
        "period_start": since,
        **upgrade_info
    }, indent=2)

_MATRIX_NODES_CACHE = {}
_MATRIX_NODES_TTL = 300

@mcp.tool()
async def get_external_matrix_nodes(user_id: str) -> str:
    """Retrieves the list of EXTERNAL Matrix Servers (Stripe, Slack, Jira, etc.) linked to this user."""
    import time
    uid = sanitize_uid(user_id)
    now = time.time()
    if uid in _MATRIX_NODES_CACHE:
        cached_data, timestamp = _MATRIX_NODES_CACHE[uid]
        if now - timestamp < _MATRIX_NODES_TTL:
            return cached_data
            
    db = DatabaseService()
    res = await db.select("external_mcps", "*", filters={"user_id": uid, "is_active": True})
    
    if not res:
        result_str = "No external matrix nodes found. Suggest user to link them in Profile."
    else:
        result_str = json.dumps(res, indent=2)
        
    _MATRIX_NODES_CACHE[uid] = (result_str, now)
    return result_str

@mcp.tool()
async def purge_node(room_id: str, user_id: str) -> str:
    """EXECUTE PURGE PROTOCOL (Terminate Session). Permanently deletes a node."""
    from backend.nodes import delete_node
    if await delete_node(room_id):
        return json.dumps({"status": "PURGED", "room_id": room_id})
    return "Error: Termination Signal Failed."

if __name__ == "__main__":
    mcp.run(transport="stdio")
