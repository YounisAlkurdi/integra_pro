from langchain_core.tools import tool
import json
from ..core.api_bridge import dispatch_sync
from ..supabase_client import supabase

@tool
def get_external_matrix_nodes(user_id: str) -> str:
    """
    RETRIEVE_EXTERNAL_LOGS: Use this to check for linked third-party services like Stripe or Slack.
    It returns the server name and available configuration.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(supabase.get("external_mcps", f"user_id=eq.{str(user_id)}&is_active=eq.true"))
    if not res:
        return "No external matrix nodes found. Suggest user to link them in Profile."
    return json.dumps(res)

@tool
def matrix_gateway(target_service: str, operation_goal: str, user_id: str, payload_json: str = "{}"):
    """
    Execute an API operation for any linked matrix service.
    
    Args:
        target_service: The name of the service (e.g., 'Stripe Matrix', 'Slack').
        operation_goal: What you want to do (e.g., 'GET /balance' or action intent).
        user_id: The unique identifier for the user.
        payload_json: A JSON string of parameters needed for the API call.
    """
    try:
        # 1. Fetch the node to get credentials
        import asyncio
        loop = asyncio.get_event_loop()
        nodes_list = loop.run_until_complete(supabase.get("external_mcps", f"user_id=eq.{str(user_id)}&is_active=eq.true"))
        
        if not nodes_list:
            return f"PROTOCOL ERROR: No services linked to this neural matrix."

        node = next((n for n in nodes_list if n['mcp_name'].lower() == target_service.lower()), None)
        
        if not node:
            return f"PROTOCOL ERROR: Service '{target_service}' is not linked."

        config = node['mcp_config']
        mcp_type = node.get('mcp_type', 'custom')
        
        provider = 'custom'
        if 'base_url' in config: provider = 'rest_api'
        elif 'mcp_url' in config: provider = 'remote_mcp'
        elif mcp_type.lower() == 'stripe' or 'stripe' in target_service.lower(): provider = 'stripe'
        elif mcp_type.lower() == 'slack' or 'slack' in target_service.lower(): provider = 'slack'
        
        payload = {}
        try: payload = json.loads(payload_json) if payload_json else {}
        except: pass

        result = dispatch_sync(provider, config, operation_goal, payload)
        
        event_marker = ""
        if any(x in operation_goal.upper() for x in ["POST", "DELETE", "PATCH", "PUT"]):
            event_marker = " [INTEGRA_SYSTEM_EVENT: {\"event\": \"matrix-update\"}]"

        return f"NEURAL LINK SUCCESS: {json.dumps(result)}{event_marker}"
        
    except Exception as e:
        return f"MATRIX CRITICAL ERROR: {str(e)}"

MATRIX_TOOLS = [
    get_external_matrix_nodes,
    matrix_gateway
]
