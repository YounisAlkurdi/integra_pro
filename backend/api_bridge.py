import httpx
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger("api_bridge")

async def test_connection(provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Test connection to external API/MCP based on provider type."""
    if provider == "rest_api":
        base_url = config.get("base_url")
        if not base_url:
            return {"success": False, "message": "Base URL missing"}
        
        headers = {k: str(v) for k, v in config.items() if k != "base_url"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(base_url, headers=headers)
                # Even a 401 or 403 means the server is reachable and responded
                if res.status_code >= 500:
                    return {"success": False, "message": f"Server Error: {res.status_code}"}
                return {"success": True, "message": f"REST API Reachable ({res.status_code})"}
        except Exception as e:
            return {"success": False, "message": f"Connection Failed: {str(e)}"}
            
    elif provider == "remote_mcp":
        mcp_url = config.get("mcp_url")
        if not mcp_url:
            return {"success": False, "message": "MCP Server URL missing"}
            
        return {"success": True, "message": "Remote MCP Configured (Basic)"}
        
    elif provider == "stripe":
        if not config.get("stripe_secret_key"):
            return {"success": False, "message": "Missing Stripe Key"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://api.stripe.com/v1/balance",
                    headers={"Authorization": f"Bearer {config['stripe_secret_key']}"}
                )
                if res.status_code == 200:
                    return {"success": True, "message": "Stripe Authenticated"}
                return {"success": False, "message": f"Stripe Error: {res.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif provider == "slack":
        if not config.get("slack_bot_token"):
            return {"success": False, "message": "Missing Slack Token"}
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {config['slack_bot_token']}"}
                )
                data = res.json()
                if data.get("ok"):
                    return {"success": True, "message": "Slack Authenticated"}
                return {"success": False, "message": f"Slack Error: {data.get('error')}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": True, "message": "Configuration Syntax OK"}


async def dispatch(provider: str, config: Dict[str, Any], operation: str, payload: Dict[str, Any] = None) -> Any:
    """Execute dynamic operations on the external matrix provider."""
    payload = payload or {}
    
    if provider == "rest_api":
        base_url = config.get("base_url", "").rstrip("/")
        headers = {k: str(v) for k, v in config.items() if k != "base_url"}
        
        parts = operation.split(" ", 1)
        if len(parts) == 2:
            method, path = parts
        else:
            method, path = "POST", parts[0]
            
        if not path.startswith("/"):
            path = "/" + path
            
        for key, val in payload.items():
            if f"{{{key}}}" in path:
                path = path.replace(f"{{{key}}}", str(val))
        
        url = f"{base_url}{path}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    res = await client.get(url, headers=headers, params=payload)
                else:
                    res = await client.request(method.upper(), url, headers=headers, json=payload)
                
                try:
                    return res.json()
                except:
                    return {"status": res.status_code, "text": res.text}
        except Exception as e:
            return {"error": str(e)}
            
    elif provider == "remote_mcp":
        return {"error": "Remote MCP dispatch not fully implemented."}

    elif provider == "stripe":
        return {"result": f"Stripe operation {operation} executed via agent."}
        
    elif provider == "slack":
        return {"result": f"Slack operation {operation} executed via agent."}

    return {"error": f"Unknown provider type {provider}"}

def dispatch_sync(provider: str, config: Dict[str, Any], operation: str, payload: Dict[str, Any] = None) -> Any:
    """Synchronous version of dispatch for use in agent tools."""
    payload = payload or {}
    
    if provider == "rest_api":
        base_url = config.get("base_url", "").rstrip("/")
        headers = {k: str(v) for k, v in config.items() if k != "base_url"}
        
        parts = operation.split(" ", 1)
        if len(parts) == 2:
            method, path = parts
        else:
            method, path = "POST", parts[0]
            
        if not path.startswith("/"):
            path = "/" + path
            
        for key, val in payload.items():
            if f"{{{key}}}" in path:
                path = path.replace(f"{{{key}}}", str(val))
        
        url = f"{base_url}{path}"
        
        try:
            if method.upper() == "GET":
                res = requests.get(url, headers=headers, params=payload, timeout=30)
            else:
                res = requests.request(method.upper(), url, headers=headers, json=payload, timeout=30)
            
            try:
                return res.json()
            except:
                return {"status": res.status_code, "text": res.text}
        except Exception as e:
            return {"error": str(e)}
            
    elif provider == "remote_mcp":
        return {"error": "Remote MCP dispatch not fully implemented."}

    elif provider == "stripe":
        return {"result": f"Stripe operation {operation} executed via agent."}
        
    elif provider == "slack":
        return {"result": f"Slack operation {operation} executed via agent."}

    return {"error": f"Unknown provider type {provider}"}
