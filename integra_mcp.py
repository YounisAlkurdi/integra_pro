import os
import json
import uuid
import datetime
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Import project modules
from nodes import get_active_streams, get_node_by_room_id, create_neural_node, get_node_stats, NodeProtocol
from logs import get_node_chat_logs
from mailer import send_interview_invitation
from auth import get_active_subscription
from payments import PRICING_DATA

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
def list_active_streams(user_id: str) -> str:
    """Scan Active Data Streams (Search by SUBJECT_IDENTIFICATION). Returns all live nodes for a user."""
    uid = sanitize_uid(user_id)
    interviews = get_active_streams(user_id=uid)
    return json.dumps(interviews, indent=2)

@mcp.tool()
def establish_secure_link(candidate_name: str, position: str, user_id: str, candidate_email: str = None, scheduled_at: str = None, questions: list[str] = None) -> str:
    """
    INITIALIZE NODE (Establish Secure Link). 
    Matches the dashboard.html form fields:
    - candidate_name: IDENTIFY_SUBJECT (Candidate Name)
    - position: ASSIGNED_ROLE (Level_4_Engineer, etc.)
    - candidate_email: DELIVERY_ADDRESS (Secure Email)
    - scheduled_at: SCHEDULED_PROTOCOL_TIME (ISO Date). If empty, initializes an INSTANT node (Now).
    - questions: Neural questions for the candidate to answer.
    """
    uid = sanitize_uid(user_id)
    
    # Logic matching dashboard.js: if no schedule, use NO_DELAY (current time)
    protocol_time = scheduled_at if scheduled_at else datetime.datetime.utcnow().isoformat()
    
    node = NodeProtocol(
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        position=position,
        questions=questions or ["Identify your core strengths.", "Explain your approach to complex system architecture."],
        scheduled_at=protocol_time
    )
    result = create_neural_node(node, user_id=uid)
    return json.dumps(result, indent=2)

@mcp.tool()
def transmit_invitation_protocol(candidate_name: str, candidate_email: str, scheduled_at: str, room_id: str) -> str:
    """TRANSMIT INVITATION (Send Email). Dispatches the secure link to the target address."""
    domain = os.getenv("APP_DOMAIN", "https://tist-integra.vercel.app")
    room_link = f"{domain}/integra-session.html?room={room_id}&role=candidate"
    
    return send_interview_invitation(candidate_name, candidate_email, scheduled_at, room_link)

# --- 2. System Intelligence & Telemetry ---

@mcp.tool()
def get_neural_link_status(user_id: str) -> str:
    """Telemetry Node: Total Nodes, Live Sessions, and Memory Capacity."""
    uid = sanitize_uid(user_id)
    stats = get_node_stats(user_id=uid)
    return json.dumps(stats, indent=2)

@mcp.tool()
def sync_neural_quotas(user_id: str) -> str:
    """Retrieves Subscription Plan (Quotas, Limits, and Enforcements)."""
    uid = sanitize_uid(user_id)
    from nodes import _supabase_request
    res = _supabase_request("GET", f"user_settings?user_id=eq.{uid}")
    if not res: return json.dumps({"status": "FREE_TIER", "interviews_limit": 5, "usage": 0})
    return json.dumps(res[0], indent=2)

@mcp.tool()
def purge_node(room_id: str, user_id: str) -> str:
    """EXECUTE PURGE PROTOCOL (Terminate Session). Permanently deletes a node and clears neural buffers."""
    from main import remove_node
    uid = sanitize_uid(user_id)
    # Note: Handled by API call in main.py, but we wrap it here for Agent access
    from nodes import delete_node
    if delete_node(room_id):
        return json.dumps({"status": "PURGED", "room_id": room_id})
    return "Error: Termination Signal Failed."

if __name__ == "__main__":
    mcp.run(transport="stdio")
