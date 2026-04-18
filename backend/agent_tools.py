from langchain_core.tools import tool
import json
import integra_mcp

# --- UNIVERSAL PROTOCOL TOOL ---

@tool
def execute_establish_secure_link(candidate_name: str = "", position: str = "", user_id: str = "", candidate_email: str = None, scheduled_at: str = None, questions: list[str] = None) -> str:
    """
    Initialize a secure interview node session.
    Use this when requested to set up an interview.
    """
    if position == "" and "{" in candidate_name:
        try:
            data = json.loads(candidate_name)
            candidate_name = data.get("candidate_name", candidate_name)
            position = data.get("position", position)
            user_id = data.get("user_id", user_id)
            candidate_email = data.get("candidate_email", candidate_email)
            scheduled_at = data.get("scheduled_at", scheduled_at)
            questions = data.get("questions", questions)
        except Exception:
            pass

    try:
        return integra_mcp.establish_secure_link(
            candidate_name=candidate_name,
            position=position,
            user_id=str(user_id),
            candidate_email=candidate_email,
            scheduled_at=scheduled_at,
            questions=questions
        )
    except Exception as e:
        return f"CRITICAL_FAILURE: Protocol corruption. Error: {str(e)}"

@tool
def execute_transmit_invitation(candidate_name: str = "", candidate_email: str = "", scheduled_at: str = "", room_id: str = "") -> str:
    """
    Dispatch an interview invitation email to the candidate.
    """
    if candidate_email == "" and "{" in candidate_name:
        try:
            data = json.loads(candidate_name)
            candidate_name = data.get("candidate_name", candidate_name)
            candidate_email = data.get("candidate_email", candidate_email)
            scheduled_at = data.get("scheduled_at", scheduled_at)
            room_id = data.get("room_id", room_id)
        except Exception:
            pass

    try:
        return integra_mcp.transmit_invitation_protocol(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            scheduled_at=scheduled_at,
            room_id=room_id
        )
    except Exception as e:
        return f"CRITICAL_FAILURE: Transmission failed. Error: {str(e)}"

@tool
def get_neural_telemetry(user_id: str = "") -> str:
    """Retrieve system stats for a user_id."""
    if "{" in user_id:
        try: user_id = json.loads(user_id).get("user_id", user_id)
        except: pass
    return integra_mcp.get_neural_link_status(str(user_id))

@tool
def sync_neural_quotas(user_id: str = "") -> str:
    """Sync plan limits for a user_id."""
    if "{" in user_id:
        try: user_id = json.loads(user_id).get("user_id", user_id)
        except: pass
    return integra_mcp.sync_neural_quotas(str(user_id))

@tool
def execute_purge_protocol(room_id: str = "", user_id: str = "") -> str:
    """Terminate and purge an active interview node session."""
    if user_id == "" and "{" in room_id:
        try:
            data = json.loads(room_id)
            room_id = data.get("room_id", room_id)
            user_id = data.get("user_id", user_id)
        except Exception:
            pass
    try:
        return integra_mcp.purge_node(room_id, str(user_id))
    except Exception as e:
        return f"CRITICAL_FAILURE: Purge aborted. Error: {str(e)}"

@tool
def get_external_matrix_nodes(user_id: str = "") -> str:
    """
    RETRIEVE_EXTERNAL_LOGS: Use this to check for linked third-party services like Stripe or Slack.
    It returns the server name and available configuration.
    """
    if "{" in user_id:
        try: user_id = json.loads(user_id).get("user_id", user_id)
        except: pass
    return integra_mcp.get_external_matrix_nodes(str(user_id))

# --- UNIVERSAL NEURAL GATEWAY ---
import api_bridge

@tool
def matrix_gateway(target_service: str = "", operation_goal: str = "", payload_json: str = "{}", user_id: str = ""):
    """
    Execute an API operation for any linked matrix service.
    
    Args:
        target_service: The name of the service (e.g., 'Stripe Matrix', 'Slack').
        operation_goal: What you want to do (e.g., 'GET /balance' or action intent).
        payload_json: A JSON string of parameters needed for the API call.
        user_id: The unique identifier for the user.
    """
    if operation_goal == "" and "{" in target_service:
        try:
            data = json.loads(target_service)
            target_service = data.get("target_service", target_service)
            operation_goal = data.get("operation_goal", operation_goal)
            payload_json = data.get("payload_json", payload_json)
            user_id = data.get("user_id", user_id)
            if not isinstance(payload_json, str):
                payload_json = json.dumps(payload_json)
        except Exception:
            pass
    try:
        # 1. Fetch the node to get credentials
        nodes = get_external_matrix_nodes(str(user_id))
        node = next((n for n in json.loads(nodes) if n['mcp_name'].lower() == target_service.lower()), None)
        
        if not node:
            return f"PROTOCOL ERROR: Service '{target_service}' is not linked to this neural matrix."

        config = node['mcp_config']
        mcp_type = node.get('mcp_type', 'custom')
        
        # Determine provider explicitly
        provider = 'custom'
        if 'command' in config:
            provider = 'local_mcp'
        elif 'base_url' in config:
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

@tool
def analyze_web_link(url: str) -> str:
    """
    THE WEB SENSOR: Fetches a URL and returns a summary. Use for dealing with links output.
    """
    try:
        import httpx
        res = httpx.get(url, timeout=10.0, follow_redirects=True)
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
def analyze_image(image_path_or_url: str) -> str:
    """
    THE VISION SENSOR: Downloads an image, extracts tech data, and returns path for display.
    """
    try:
        import os
        import httpx
        file_path = image_path_or_url
        if image_path_or_url.startswith("http"):
            temp_dir = os.path.join(os.getcwd(), 'static', 'temp_images')
            os.makedirs(temp_dir, exist_ok=True)
            filename = image_path_or_url.split("/")[-1] or "downloaded_img.jpg"
            if "?" in filename: filename = filename.split("?")[0]
            file_path = os.path.join(temp_dir, filename)
            
            res = httpx.get(image_path_or_url, follow_redirects=True)
            with open(file_path, 'wb') as f:
                f.write(res.content)
            serve_path = f"/static/temp_images/{filename}"
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
def analyze_local_file(filepath: str) -> str:
    """
    THE DOCUMENT SENSOR: Reads a local file up to 500KB. Fails securely if reading sensitive env files.
    """
    import os
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
