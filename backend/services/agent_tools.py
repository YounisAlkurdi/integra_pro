import json
import logging
import httpx
from langchain_core.tools import tool
from . import integra_mcp
from .api_bridge import APIBridge

logger = logging.getLogger(__name__)

# --- UNIVERSAL PROTOCOL TOOLS ---

@tool
async def execute_establish_secure_link(candidate_name: str, position: str, user_id: str, candidate_email: str = None, scheduled_at: str = None, questions: list[str] = None) -> str:
    """Initialize a secure interview node session. Use this when requested to set up an interview."""
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
    """Dispatch an interview invitation email to the candidate."""
    try:
        res = await integra_mcp.transmit_invitation_protocol(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            scheduled_at=scheduled_at,
            room_id=room_id
        )
        return f"TRANSMISSION_RESULT: {res}"
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
        res = await integra_mcp.purge_node(room_id, str(user_id))
        return f"NEURAL LINK TERMINATED: {res} [INTEGRA_SYSTEM_EVENT: {{\"event\": \"node-deleted\"}}]"
    except Exception as e:
        return f"CRITICAL_FAILURE: Purge aborted. Error: {str(e)}"

@tool
async def get_external_matrix_nodes(user_id: str) -> str:
    """Retrieves linked third-party services like Stripe or Slack."""
    return await integra_mcp.get_external_matrix_nodes(str(user_id))

@tool
async def matrix_gateway(target_service: str, operation_goal: str, user_id: str, payload_json: str = "{}"):
    """Execute an API operation for any linked matrix service."""
    try:
        nodes_str = await get_external_matrix_nodes(str(user_id))
        if nodes_str.startswith("Error"): return f"GATEWAY ERROR: {nodes_str}"
        
        try:
            nodes_list = json.loads(nodes_str)
        except:
            return f"GATEWAY ERROR: {nodes_str}"

        if not isinstance(nodes_list, list):
            return f"GATEWAY ERROR: Service list is invalid."

        node = next((n for n in nodes_list if n['mcp_name'].lower() == target_service.lower()), None)
        if not node:
            return f"PROTOCOL ERROR: Service '{target_service}' is not linked."

        config = node['mcp_config']
        mcp_type = node.get('mcp_type', 'custom').lower()
        
        # Determine provider
        provider = 'rest_api'
        if 'stripe' in target_service.lower() or mcp_type == 'stripe': provider = 'stripe'
        elif 'slack' in target_service.lower() or mcp_type == 'slack': provider = 'slack'
        elif 'mcp_url' in config: provider = 'remote_mcp'
        
        payload = json.loads(payload_json) if payload_json else {}
        result = await APIBridge.dispatch(provider, config, operation_goal, payload)
        
        event_marker = ""
        if any(x in operation_goal.upper() for x in ["POST", "DELETE", "PATCH", "PUT"]):
            event_marker = " [INTEGRA_SYSTEM_EVENT: {\"event\": \"matrix-update\"}]"

        return f"NEURAL LINK SUCCESS: {json.dumps(result)}{event_marker}"
    except Exception as e:
        return f"MATRIX CRITICAL ERROR: {str(e)}"

@tool
async def analyze_web_link(url: str) -> str:
    """Fetches a URL and returns a summary."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            res = await client.get(url)
            html = res.text
            
            # Simple title/content extraction
            import re
            m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            title = m.group(1) if m else "Unknown Title"
            summary = html[:300].strip() + "..."
            
            payload = {"type": "link", "url": url, "title": title, "summary": summary}
            return f"[INTEGRA_UI_CARD: {json.dumps(payload)}]"
    except Exception as e:
        return f"Web Sensor Failure: {str(e)}"

@tool
async def analyze_image(image_path_or_url: str) -> str:
    """The Vision Sensor: Downloads/Analyzes an image and returns path for display."""
    try:
        import os
        file_path = image_path_or_url
        if image_path_or_url.startswith("http"):
            temp_dir = os.path.join(os.getcwd(), 'static', 'temp_images')
            os.makedirs(temp_dir, exist_ok=True)
            filename = image_path_or_url.split("/")[-1] or "downloaded_img.jpg"
            if "?" in filename: filename = filename.split("?")[0]
            file_path = os.path.join(temp_dir, filename)
            
            async with httpx.AsyncClient() as client:
                res = await client.get(image_path_or_url, follow_redirects=True)
                with open(file_path, 'wb') as f:
                    f.write(res.content)
            serve_path = f"/static/temp_images/{filename}"
        else:
            serve_path = image_path_or_url
            
        return f"[INTEGRA_UI_CARD: {json.dumps({'type': 'image', 'path': serve_path})}]"
    except Exception as e:
        return f"Vision Sensor Failure: {str(e)}"

@tool
async def analyze_local_file(filepath: str) -> str:
    """The Document Sensor: Reads a local file (max 500KB). Secure block on env files."""
    import os
    try:
        name = filepath.lower()
        if any(x in name for x in [".env", "secret", ".pem", "key"]):
            return "SECURITY ERROR: Prevented neural read on sensitive file."
            
        if not os.path.exists(filepath):
            return "Document Sensor Error: File not found."
            
        if os.path.getsize(filepath) > 500 * 1024:
            return "Document Sensor Error: File too large."
            
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        return f"[INTEGRA_UI_CARD: {json.dumps({'type': 'file', 'filepath': filepath, 'content': content})}]"
    except Exception as e:
        return f"Document Sensor Failure: {str(e)}"

@tool
async def get_available_neural_skills() -> str:
    """Lists available skill modules from the Integra Skill Library."""
    import os
    try:
        skills_dir = os.path.join(os.getcwd(), 'awesome-claude-skills')
        if not os.path.exists(skills_dir):
            return "Skill Library not found."
        
        skills = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)) and not d.startswith('.')]
        return f"AVAILABLE NEURAL SKILLS: {', '.join(skills)}"
    except Exception as e:
        return f"Skill Retrieval Failure: {str(e)}"

@tool
async def load_neural_skill(skill_name: str) -> str:
    """Loads the documentation and instructions for a specific skill module."""
    import os
    try:
        skill_path = os.path.join(os.getcwd(), 'awesome-claude-skills', skill_name, 'SKILL.md')
        if not os.path.exists(skill_path):
            return f"Skill '{skill_name}' not found or missing SKILL.md."
            
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return f"SKILL LOADED [{skill_name}]:\n\n{content}\n\n[SYSTEM: You now have the instructions for this skill. Apply them to the current task.]"
    except Exception as e:
        return f"Skill Load Failure: {str(e)}"

# Tools Export
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
    analyze_local_file,
    get_available_neural_skills,
    load_neural_skill
]
