import os
import json
import datetime
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Use relative imports in backend folder
from .nodes import get_active_streams, create_neural_node, get_node_stats, NodeProtocol, delete_node
from .mailer import send_interview_invitation
from .auth import get_active_subscription
from .supabase_client import supabase

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

# --- 1. Operations: Node Management ---

@mcp.tool()
async def list_active_streams(user_id: str) -> str:
    """Scan Active Data Streams. Returns all live nodes for a user."""
    uid = sanitize_uid(user_id)
    sub = await get_active_subscription(uid)
    since = sub.get('created_at') if sub else None
    interviews = await get_active_streams(user_id=uid, since_date=since)
    return json.dumps(interviews, indent=2)

@mcp.tool()
async def establish_secure_link(candidate_name: str, position: str, user_id: str, candidate_email: str = None, scheduled_at: str = None, questions: list[str] = None) -> str:
    """Initialize a secure interview node session."""
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
    
    return await send_interview_invitation(candidate_name, candidate_email, scheduled_at, room_link)

# --- 2. System Intelligence & Telemetry ---

@mcp.tool()
async def get_neural_link_status(user_id: str) -> str:
    """Telemetry Node: Total Nodes, Live Sessions, and Memory Capacity."""
    uid = sanitize_uid(user_id)
    sub = await get_active_subscription(uid)
    since = sub.get('created_at') if sub else None
    stats = await get_node_stats(user_id=uid, since_date=since)
    return json.dumps(stats, indent=2)

@mcp.tool()
async def sync_neural_quotas(user_id: str) -> str:
    """Retrieves the ACTUAL Subscription Plan from the LIVE billing system."""
    uid = sanitize_uid(user_id)
    sub = await get_active_subscription(uid)
    
    upgrade_info = {
        "upgrade_links": {
            "professional": "/upgrade?plan=professional",
            "nexus": "/upgrade?plan=nexus"
        },
        "instructions": "If the user is out of slots, suggest they visit the upgrade links above."
    }
    
    stats = await get_node_stats(uid, since_date=sub.get('created_at') if sub else None)
    
    if not sub: 
        return json.dumps({
            "status": "FREE_TIER", 
            "interviews_limit": 5, 
            "usage_count": stats.get('total', 0), 
            **upgrade_info
        })
    
    return json.dumps({
        "plan_id": sub.get('plan_id'),
        "status": sub.get('status'),
        "interviews_limit": sub.get('interviews_limit'),
        "usage_count": stats.get('total', 0),
        "period_start": sub.get('created_at'),
        **upgrade_info
    }, indent=2)

@mcp.tool()
async def get_external_matrix_nodes(user_id: str) -> str:
    """Retrieves the list of EXTERNAL Matrix Servers linked to this user."""
    uid = sanitize_uid(user_id)
    res = await supabase.get("external_mcps", f"user_id=eq.{uid}&is_active=eq.true", use_cache=True)
    
    if not res:
        return "No external matrix nodes found. Suggest user to link them in Profile."
    return json.dumps(res, indent=2)

@mcp.tool()
async def purge_node_protocol(room_id: str, user_id: str) -> str:
    """EXECUTE PURGE PROTOCOL (Terminate Session). Permanently deletes a node."""
    if await delete_node(room_id):
        return json.dumps({"status": "PURGED", "room_id": room_id})
    return "Error: Termination Signal Failed."

if __name__ == "__main__":
    mcp.run(transport="stdio")
