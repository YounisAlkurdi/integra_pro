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
mcp = FastMCP("Integra Control Node")

# --- Helper: Get Default User ID ---
# Since this is a server for a specific project, we might need a default user_id if not provided.
# In a real scenario, this would come from the session context, but here we can try to fetch the first user who has a subscription.
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID") # Can be set in .env

# --- 1. Core Management ---

@mcp.tool()
def list_interviews(user_id: str = None) -> str:
    """
    List all active interview sessions (nodes) for a user.
    If user_id is not provided, uses the default system user.
    """
    uid = user_id or DEFAULT_USER_ID
    if not uid:
        return "Error: User ID required."
    
    interviews = get_active_streams(user_id=uid)
    return json.dumps(interviews, indent=2)

@mcp.tool()
def get_interview_details(room_id: str) -> str:
    """
    Gets metadata and configuration for a specific interview room.
    """
    node = get_node_by_room_id(room_id)
    if not node:
        return f"Error: Room {room_id} not found."
    return json.dumps(node, indent=2)

@mcp.tool()
def create_interview(candidate_name: str, position: str, questions: list[str], scheduled_at: str, user_id: str = None) -> str:
    """
    Initializes a new interview session.
    questions: A list of strings representing the interview questions.
    scheduled_at: ISO format date string.
    """
    uid = user_id or DEFAULT_USER_ID
    if not uid:
        return "Error: User ID required."
    
    node = NodeProtocol(
        candidate_name=candidate_name,
        position=position,
        questions=questions,
        scheduled_at=scheduled_at
    )
    
    result = create_neural_node(node, user_id=uid)
    return json.dumps(result, indent=2)

# --- 2. Transcripts & Analysis ---

@mcp.tool()
def get_interview_transcript(room_id: str, user_id: str = None) -> str:
    """
    Retrieves the full chat transcript/logs for a specific interview room.
    """
    uid = user_id or DEFAULT_USER_ID
    if not uid:
        # Try to find user_id from the node if not provided
        node = get_node_by_room_id(room_id)
        if node:
            uid = node.get('user_id')
    
    if not uid:
        return "Error: User ID required."
        
    logs = get_node_chat_logs(room_id, user_id=uid)
    return json.dumps(logs, indent=2)

@mcp.tool()
def analyze_interview(room_id: str, user_id: str = None) -> str:
    """
    (Advanced) Fetches the transcript and provides a high-level summary and candidate performance evaluation.
    Note: This tool uses the Agent's internal logic to analyze the data provided by get_interview_transcript.
    """
    uid = user_id or DEFAULT_USER_ID
    if not uid:
        node = get_node_by_room_id(room_id)
        if node: uid = node.get('user_id')
        
    if not uid:
        return "Error: User ID required."
        
    logs = get_node_chat_logs(room_id, user_id=uid)
    if not logs:
        return "Analysis: No conversation found for this room."
    
    # In a real MCP server, this would just return the text for the agent to process.
    # Since the agent IS the analyzer here, we'll return a formatted string of the logs.
    transcript = "\n".join([f"[{l['sender']}]: {l['message']}" for l in logs])
    return f"Transcription Data Found. Please analyze the following transcript:\n\n{transcript}"

# --- 3. Communication ---

@mcp.tool()
def send_invitation(candidate_name: str, candidate_email: str, scheduled_at: str, room_link: str) -> str:
    """
    Sends an automated interview invitation email to a candidate.
    """
    try:
        result = send_interview_invitation(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            scheduled_at=scheduled_at,
            room_link=room_link
        )
        return f"Success: Invitation sent to {candidate_email}. (ID: {result.get('id')})"
    except Exception as e:
        return f"Error: Failed to send invitation: {str(e)}"

# --- 4. Usage & Billing ---

@mcp.tool()
def get_usage_stats(user_id: str = None) -> str:
    """
    Checks current subscription limits and interview consumption.
    """
    uid = user_id or DEFAULT_USER_ID
    if not uid:
        return "Error: User ID required."
        
    stats = get_node_stats(user_id=uid)
    sub = get_active_subscription(user_id=uid)
    
    report = {
        "telemetry": stats,
        "subscription": sub
    }
    return json.dumps(report, indent=2)

@mcp.tool()
def list_invoices(user_id: str = None) -> str:
    """
    Retrieves the billing history and paid invoices for a user.
    """
    uid = user_id or DEFAULT_USER_ID
    if not uid:
        return "Error: User ID required."
        
    # We use a manual Supabase request for invoices since it's not and-packaged in a function
    from nodes import _supabase_request
    invoices = _supabase_request("GET", f"invoices?user_id=eq.{uid}&order=created_at.desc")
    return json.dumps(invoices, indent=2)

# --- 5. Security & health ---

@mcp.tool()
def get_security_alerts() -> str:
    """
    Scans the security_threats.log for price tampering or suspicious activity.
    """
    log_path = "security_threats.log"
    if not os.path.exists(log_path):
        return "Security Report: No threats detected (Log file missing)."
    
    with open(log_path, "r") as f:
        logs = f.readlines()
        
    if not logs:
        return "Security Report: Log file empty. System clean."
        
    # Return last 20 entries
    return "Recent Security Alerts:\n" + "".join(logs[-20:])

@mcp.tool()
def check_system_health() -> str:
    """
    Verifies system connectivity and environment readiness.
    """
    from nodes import _supabase_request
    health = {
        "timestamp": str(datetime.datetime.now()),
        "env_check": {
            "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
            "STRIPE_KEY": bool(os.getenv("STRIPE_SECRET_KEY")),
            "LIVEKIT_KEY": bool(os.getenv("LIVEKIT_API_KEY"))
        },
        "neural_link": "DISCONNECTED"
    }
    
    # Try a simple Supabase query
    try:
        res = _supabase_request("GET", "nodes?limit=1")
        health["neural_link"] = "CONNECTED"
    except:
        pass
        
    return json.dumps(health, indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
