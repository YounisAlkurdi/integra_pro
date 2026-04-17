import os
import json
import datetime
import logging
from mcp.server.fastmcp import FastMCP
from ..core.supabase_client import get_supabase_client
from ..core.auth import get_active_subscription
from ..routes.nodes import get_active_streams, create_neural_node, get_node_stats, delete_node, NodeProtocol
from .mailer import Mailer

logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP("Integra Neural Command")

def sanitize_uid(uid: str) -> str:
    if not uid: return ""
    uid = str(uid).strip()
    if uid.startswith('{') and 'user_id' in uid:
        try:
            data = json.loads(uid)
            return data.get('user_id', uid)
        except: pass
    return uid

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
    domain = get_env_safe("APP_DOMAIN", "https://tist-integra.vercel.app")
    room_link = f"{domain}/integra-session.html?room={room_id}&role=candidate"
    
    mailer = Mailer()
    res = mailer.send_interview_invitation(candidate_name, candidate_email, scheduled_at, room_link)
    return json.dumps(res)

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
    """Retrieves the ACTUAL Subscription Plan and Enforcements."""
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
    stats = await get_node_stats(uid, since_date=since)
    
    return json.dumps({
        "plan_id": sub.get('plan_id'),
        "status": sub.get('status'),
        "interviews_limit": sub.get('interviews_limit'),
        "usage_count": stats.get('total', 0),
        "period_start": since,
        **upgrade_info
    }, indent=2)

@mcp.tool()
async def get_external_matrix_nodes(user_id: str) -> str:
    """Retrieves the list of EXTERNAL Matrix Servers linked to this user."""
    client = get_supabase_client()
    uid = sanitize_uid(user_id)
    
    try:
        res = await client.from_("external_mcps").select("*").eq("user_id", uid).eq("is_active", True).execute()
        if not res.data:
            return "No external matrix nodes found. Suggest user to link them in Profile."
        return json.dumps(res.data, indent=2)
    except Exception as e:
        logger.error(f"Failed to fetch external matrix nodes: {e}")
        return f"Error: {e}"

@mcp.tool()
async def purge_node(room_id: str, user_id: str) -> str:
    """EXECUTE PURGE PROTOCOL (Terminate Session). Permanently deletes a node."""
    uid = sanitize_uid(user_id)
    if await delete_node(room_id, user_id=uid):
        return json.dumps({"status": "PURGED", "room_id": room_id})
    return "Error: Termination Signal Failed."

def get_env_safe(key, default=None):
    return os.getenv(key, default)

if __name__ == "__main__":
    mcp.run(transport="stdio")
