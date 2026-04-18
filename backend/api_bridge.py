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

    elif provider == "local_mcp":
        command = config.get("command")
        if not command:
            return {"success": False, "message": "Local MCP command missing"}
        return {"success": True, "message": f"Local MCP configured to run: {command}"}
        
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
        mcp_url = config.get("mcp_url")
        if not mcp_url:
            return {"error": "Missing MCP URL in config"}
            
        # Ensure we connect to the SSE endpoint
        if not mcp_url.rstrip("/").endswith("sse"):
            mcp_url = mcp_url.rstrip("/") + "/sse"
            
        op_parts = operation.split(" ", 1)
        action = op_parts[0]
        
        try:
            from mcp.client.sse import sse_client
            from mcp.client.session import ClientSession
            
            headers = {}
            if "apikey" in config:
                key = str(config['apikey']).strip()
                headers["Authorization"] = f"Bearer {key}"
                headers["X-Api-Key"] = key
            elif "token" in config:
                key = str(config['token']).strip()
                headers["Authorization"] = f"Bearer {key}"
                headers["X-Api-Key"] = key
                
            async with sse_client(url=mcp_url, headers=headers) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    
                    if action == "list_tools":
                        result = await session.list_tools()
                        return {"tools": [{"name": t.name, "description": t.description, "inputSchema": getattr(t, 'inputSchema', {})} for t in result.tools]}
                    elif action == "call_tool":
                        tool_name = op_parts[1] if len(op_parts) > 1 else payload.get("name")
                        args = payload.get("arguments", payload)
                        result = await session.call_tool(tool_name, arguments=args)
                        return {"result": [getattr(c, "text", str(c)) for c in result.content]}
                    else:
                        return {"error": f"Unsupported remote_mcp action: {action}"}
        except Exception as e:
            logger.error(f"Remote MCP Async Error: {e}")
            if "401" in str(e):
                return {"error": "401 Unauthorized: Please check your Smithery API key and ensure you have authorized the server at https://smithery.ai"}
            return {"error": f"Remote MCP Error: {str(e)}"}

    elif provider == "local_mcp":
        command = config.get("command")
        args = config.get("args", [])
        env = config.get("env", None)
        
        op_parts = operation.split(" ", 1)
        action = op_parts[0]

        try:
            from mcp.client.stdio import stdio_client, StdioServerParameters
            from mcp.client.session import ClientSession

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )

            async with stdio_client(server_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    
                    if action == "list_tools":
                        result = await session.list_tools()
                        return {"tools": [{"name": t.name, "description": t.description, "inputSchema": getattr(t, 'inputSchema', {})} for t in result.tools]}
                    elif action == "call_tool":
                        tool_name = op_parts[1] if len(op_parts) > 1 else payload.get("name")
                        args_payload = payload.get("arguments", payload)
                        result = await session.call_tool(tool_name, arguments=args_payload)
                        return {"result": [getattr(c, "text", str(c)) for c in result.content]}
                    else:
                        return {"error": f"Unsupported local_mcp action: {action}"}
        except Exception as e:
            logger.error(f"Local MCP Async Error: {e}")
            return {"error": f"Local MCP Error: {str(e)}"}

    elif provider == "stripe":
        return {"result": f"Stripe operation {operation} executed via agent."}
        
    elif provider == "slack":
        return {"result": f"Slack operation {operation} executed via agent."}

    return {"error": f"Unknown provider type {provider}"}

def dispatch_sync(provider: str, config: Dict[str, Any], operation: str, payload: Dict[str, Any] = None) -> Any:
    """Synchronous version of dispatch for use in agent tools."""
    import asyncio
    
    # Using a new event loop to ensure compatibility with various sync callers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(dispatch(provider, config, operation, payload))
    except Exception as e:
        logger.error(f"Dispatch Sync Error: {e}")
        return {"error": str(e)}
    finally:
        loop.close()
