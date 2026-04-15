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

@tool
def get_external_matrix_nodes(user_id: str) -> str:
    """
    RETRIEVE_EXTERNAL_LOGS: Use this to check for linked third-party services like Stripe or Slack.
    It returns the server name and available configuration.
    """
    return integra_mcp.get_external_matrix_nodes(str(user_id))

# --- UNIVERSAL NEURAL GATEWAY ---
import api_bridge

@tool
def matrix_gateway(target_service: str, operation_goal: str, payload_json: str = "{}"):
    """
    UNIVERSAL GATEWAY: Executes an authenticated API operation for ANY linked matrix service.
    
    Args:
        target_service: The name of the service (e.g., 'Stripe Matrix', 'Slack', or custom REST API).
        operation_goal: What you want to do (e.g., 'GET /balance' or 'POST /users').
        payload_json: A JSON string of parameters needed for the API call.
    """
    try:
        # 1. Fetch the node to get credentials
        nodes = get_external_matrix_nodes("") # Self-resolving via user_id inside
        node = next((n for n in json.loads(nodes) if n['mcp_name'].lower() == target_service.lower()), None)
        
        if not node:
            return f"PROTOCOL ERROR: Service '{target_service}' is not linked to this neural matrix."

        config = node['mcp_config']
        mcp_type = node.get('mcp_type', 'custom')
        
        # Determine provider explicitly
        provider = 'custom'
        if 'base_url' in config:
            provider = 'rest_api'
        elif 'mcp_url' in config:
            provider = 'remote_mcp'
        elif mcp_type.lower() == 'stripe' or 'stripe' in target_service.lower():
            provider = 'stripe'
        elif mcp_type.lower() == 'slack' or 'slack' in target_service.lower():
            provider = 'slack'
        elif mcp_type.lower() == 'rest_api':
            provider = 'rest_api'
        elif mcp_type.lower() == 'remote_mcp':
            provider = 'remote_mcp'
        
        # Parse payload
        payload = {}
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except:
            pass

        result = api_bridge.dispatch_sync(provider, config, operation_goal, payload)
        
        if "error" in result:
             return f"GATEWAY ERROR: {result['error']}"
             
        return f"NEURAL LINK SUCCESS: {json.dumps(result)}"
        
    except Exception as e:
        return f"MATRIX CRITICAL ERROR: {str(e)}"

# Export all tools for the AI Agent
INTEGRA_TOOLS = [
    execute_establish_secure_link,
    execute_transmit_invitation,
    get_neural_telemetry,
    sync_neural_quotas,
    execute_purge_protocol,
    get_external_matrix_nodes,
    matrix_gateway
]
