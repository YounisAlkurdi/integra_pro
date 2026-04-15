from langchain_core.tools import tool
import json
import integra_mcp

# --- UNIVERSAL PROTOCOL TOOL ---
# We use a single string input to ensure ReAct agents don't fail during validation.
# The Agent will pass a JSON string, and we will parse it.

@tool
def execute_establish_secure_link(json_input: str) -> str:
    """
    EXECUTE_LINK_PROTOCOL: Use this to INITIALIZE A NODE.
    Input MUST be a JSON string with these keys: 
    {"candidate_name": "...", "position": "...", "user_id": "...", "candidate_email": "...", "scheduled_at": "..."}
    If 'scheduled_at' is missing, it creates an INSTANT session.
    """
    try:
        data = json.loads(json_input)
        return integra_mcp.establish_secure_link(
            candidate_name=data.get("candidate_name"),
            position=data.get("position"),
            user_id=str(data.get("user_id")),
            candidate_email=data.get("candidate_email"),
            scheduled_at=data.get("scheduled_at"),
            questions=data.get("questions")
        )
    except Exception as e:
        return f"CRITICAL_FAILURE: Protocol corruption. Ensure valid JSON input. Error: {str(e)}"

@tool
def execute_transmit_invitation(json_input: str) -> str:
    """
    EXECUTE_TRANSMIT_PROTOCOL: Use this to DISPATCH THE INVITATION.
    Input MUST be a JSON string with these keys:
    {"candidate_name": "...", "candidate_email": "...", "scheduled_at": "...", "room_id": "..."}
    """
    try:
        data = json.loads(json_input)
        return integra_mcp.transmit_invitation_protocol(
            candidate_name=data.get("candidate_name"),
            candidate_email=data.get("candidate_email"),
            scheduled_at=data.get("scheduled_at"),
            room_id=data.get("room_id")
        )
    except Exception as e:
        return f"CRITICAL_FAILURE: Transmission failed. Error: {str(e)}"

@tool
def get_neural_telemetry(user_id: str) -> str:
    """Retrieve system stats for a user_id."""
    return integra_mcp.get_neural_link_status(str(user_id))

@tool
def sync_neural_quotas(user_id: str) -> str:
    """Sync plan limits for a user_id."""
    return integra_mcp.sync_neural_quotas(str(user_id))

@tool
def execute_purge_protocol(json_input: str) -> str:
    """PURGE_PROTOCOL: Terminate a node. Input: {"room_id": "...", "user_id": "..."}"""
    try:
        data = json.loads(json_input)
        return integra_mcp.purge_node(data.get("room_id"), str(data.get("user_id")))
    except Exception as e:
        return f"CRITICAL_FAILURE: Purge aborted. Error: {str(e)}"

# Export all tools for the AI Agent
INTEGRA_TOOLS = [
    execute_establish_secure_link,
    execute_transmit_invitation,
    get_neural_telemetry,
    sync_neural_quotas,
    execute_purge_protocol
]
