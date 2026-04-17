from langchain_core.tools import tool
import json
import os
import httpx

# Absolute imports for the new structure
try:
    from backend import integra_mcp
    from backend import api_bridge
except ImportError:
    # Fallback for direct execution
    import integra_mcp
    import api_bridge

# --- UNIVERSAL PROTOCOL TOOL ---

@tool
async def execute_establish_secure_link(candidate_name: str, position: str, user_id: str, candidate_email: str = None, scheduled_at: str = None, questions: list[str] = None) -> str:
    """
    Initialize a secure interview node session.
    Use this when requested to set up an interview.
    """
    try:
        res = await integra_mcp.establish_secure_link(
            candidate_name=candidate_name,
            position=position,
            user_id=str(user_id),
            candidate_email=candidate_email,
            scheduled_at=scheduled_at,
            questions=questions
        )
        return f"NEURAL LINK ACTIVE: {res} [INTEGRA_SYSTEM_EVENT: {{\"event\": \"node-created\"}}]"
    except Exception as e:
        return f"CRITICAL_FAILURE: Protocol corruption. Error: {str(e)}"

@tool
async def execute_transmit_invitation(candidate_name: str, candidate_email: str, scheduled_at: str, room_id: str) -> str:
    """
    Dispatch an interview invitation email to the candidate.
    """
    try:
        res = await integra_mcp.transmit_invitation_protocol(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            scheduled_at=scheduled_at,
            room_id=room_id
        )
        return f"TRANSMISSION SUCCESS: {res}"
    except Exception as e:
        return f"CRITICAL_FAILURE: Transmission failed. Error: {str(e)}"

@tool
async def get_neural_telemetry(user_id: str) -> str:
    """Retrieve system stats for a user_id."""
    return await integra_mcp.get_neural_link_status(str(user_id))

@tool
async def sync_neural_quotas(user_id: str) -> str:
    """Sync plan limits for a user_id."""
    return await integra_mcp.sync_neural_quotas(str(user_id))

@tool
async def execute_purge_protocol(room_id: str, user_id: str) -> str:
    """Terminate and purge an active interview node session."""
    try:
        # Note: function name in integra_mcp.py is purge_node_protocol
        res = await integra_mcp.purge_node_protocol(room_id, str(user_id))
        return f"NEURAL LINK TERMINATED: {res} [INTEGRA_SYSTEM_EVENT: {{\"event\": \"node-deleted\"}}]"
    except Exception as e:
        return f"CRITICAL_FAILURE: Purge aborted. Error: {str(e)}"

@tool
async def get_external_matrix_nodes(user_id: str) -> str:
    """
    RETRIEVE_EXTERNAL_LOGS: Use this to check for linked third-party services like Stripe or Slack.
    It returns the server name and available configuration.
    """
    return await integra_mcp.get_external_matrix_nodes(str(user_id))

@tool
async def matrix_gateway(target_service: str, operation_goal: str, user_id: str, payload_json: str = "{}"):
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
        nodes = await get_external_matrix_nodes(str(user_id))
        try:
            nodes_list = json.loads(nodes)
        except:
            return f"GATEWAY ERROR: {nodes}"
            
        if not isinstance(nodes_list, list):
            return f"GATEWAY ERROR: {nodes}"

        node = next((n for n in nodes_list if n['mcp_name'].lower() == target_service.lower()), None)
        
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

        result = await api_bridge.dispatch_async(provider, config, operation_goal, payload)
        
        if isinstance(result, dict) and "error" in result:
             return f"GATEWAY ERROR: {result['error']}"
             
        # Add system event for refresh if it was a modification
        event_marker = ""
        if any(x in operation_goal.upper() for x in ["POST", "DELETE", "PATCH", "PUT"]):
            event_marker = " [INTEGRA_SYSTEM_EVENT: {\"event\": \"matrix-update\"}]"

        return f"NEURAL LINK SUCCESS: {json.dumps(result)}{event_marker}"
        
    except Exception as e:
        return f"MATRIX CRITICAL ERROR: {str(e)}"

@tool
async def analyze_web_link(url: str) -> str:
    """
    THE WEB SENSOR: Fetches a URL and returns a summary. Use for dealing with links output.
    """
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10.0, follow_redirects=True)
        html = res.text
        
        # Try bs4 if available, otherwise fallback
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string.strip() if soup.title else "Unknown Title"
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 50]
            summary = " ".join(paragraphs[:2]) if paragraphs else "No content summary found."
        except ImportError:
            import re
            m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            title = m.group(1) if m else "Unknown Title"
            summary = html[:300].strip() + "..."
            
        summary = summary[:300] + "..." if len(summary) > 300 else summary
        
        payload = {"type": "link", "url": url, "title": title, "summary": summary}
        return f"[INTEGRA_UI_CARD: {json.dumps(payload)}]"
    except Exception as e:
        return f"Web Sensor Failure: {str(e)}"

@tool
async def analyze_image(image_path_or_url: str) -> str:
    """
    THE VISION SENSOR: Downloads an image, extracts tech data, and returns path for display.
    """
    try:
        file_path = image_path_or_url
        if image_path_or_url.startswith("http"):
            # Path adjustment for new structure
            temp_dir = os.path.join(os.getcwd(), 'assets', 'temp_images')
            os.makedirs(temp_dir, exist_ok=True)
            filename = image_path_or_url.split("/")[-1] or "downloaded_img.jpg"
            if "?" in filename: filename = filename.split("?")[0]
            file_path = os.path.join(temp_dir, filename)
            
            async with httpx.AsyncClient() as client:
                res = await client.get(image_path_or_url, follow_redirects=True)
            with open(file_path, 'wb') as f:
                f.write(res.content)
            serve_path = f"/assets/temp_images/{filename}"
        else:
            serve_path = image_path_or_url
            
        # Try EXIF or fallback
        try:
            from PIL import Image
            img = Image.open(file_path)
            tech_data = {"format": img.format, "size": f"{img.size[0]}x{img.size[1]}", "mode": img.mode}
        except Exception:
            tech_data = {"status": "Metadata unavailable or PIL missing"}

        payload = {"type": "image", "path": serve_path, "tech_data": tech_data}
        return f"[INTEGRA_UI_CARD: {json.dumps(payload)}]"
    except Exception as e:
        return f"Vision Sensor Failure: {str(e)}"

@tool
async def analyze_local_file(filepath: str) -> str:
    """
    THE DOCUMENT SENSOR: Reads a local file up to 500KB. Fails securely if reading sensitive env files.
    """
    try:
        # Secure block
        name = filepath.lower()
        if ".env" in name or "secret" in name or ".pem" in name:
            return "SECURITY ERROR: Prevented neural read on highly sensitive file."
            
        if not os.path.exists(filepath):
            return f"Document Sensor Error: {filepath} not found."
            
        sz = os.path.getsize(filepath)
        if sz > 500 * 1024:
            return "Document Sensor Error: File exceeds 500KB strict limit."
            
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        payload = {
            "type": "file",
            "filepath": filepath,
            "content": content
        }
        return f"[INTEGRA_UI_CARD: {json.dumps(payload)}]"
    except Exception as e:
        return f"Document Sensor Failure: {str(e)}"

# Export all tools for the AI Agent
INTEGRA_TOOLS = [
    execute_establish_secure_link,
    execute_transmit_invitation,
    get_neural_telemetry,
    sync_neural_quotas,
    execute_purge_protocol,
    get_external_matrix_nodes,
    matrix_gateway,
    analyze_web_link,
    analyze_image,
    analyze_local_file
]
