import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class APIBridge:
    """Service to bridge communication with external APIs and Matrix Providers."""
    
    @staticmethod
    async def test_connection(provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to external API based on provider type."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if provider == "rest_api":
                    base_url = config.get("base_url")
                    if not base_url: return {"success": False, "message": "Base URL missing"}
                    headers = {k: str(v) for k, v in config.items() if k != "base_url"}
                    res = await client.get(base_url, headers=headers)
                    return {"success": True, "message": f"REST API Reachable ({res.status_code})"}
                    
                elif provider == "stripe":
                    key = config.get("stripe_secret_key")
                    if not key: return {"success": False, "message": "Missing Stripe Key"}
                    res = await client.get("https://api.stripe.com/v1/balance", headers={"Authorization": f"Bearer {key}"})
                    return {"success": res.status_code == 200, "message": "Stripe Authenticated" if res.status_code == 200 else f"Stripe Error: {res.status_code}"}
                    
                elif provider == "slack":
                    token = config.get("slack_bot_token")
                    if not token: return {"success": False, "message": "Missing Slack Token"}
                    res = await client.post("https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {token}"})
                    data = res.json()
                    return {"success": data.get("ok"), "message": "Slack Authenticated" if data.get("ok") else f"Slack Error: {data.get('error')}"}
                    
            return {"success": True, "message": "Configuration Syntax OK"}
        except Exception as e:
            logger.error(f"Connection test failed for {provider}: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    async def dispatch(provider: str, config: Dict[str, Any], operation: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Execute operations on the external provider."""
        payload = payload or {}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if provider == "rest_api":
                    return await APIBridge._dispatch_rest(client, config, operation, payload)
                elif provider == "stripe":
                    return await APIBridge._dispatch_stripe(client, config, operation, payload)
                elif provider == "slack":
                    return await APIBridge._dispatch_slack(client, config, operation, payload)
                else:
                    return {"error": f"Unknown provider: {provider}"}
        except Exception as e:
            logger.error(f"Dispatch failed for {provider}: {e}")
            return {"error": str(e)}

    @staticmethod
    async def _dispatch_rest(client, config, operation, payload):
        base_url = config.get("base_url", "").rstrip("/")
        headers = {k: str(v) for k, v in config.items() if k != "base_url"}
        parts = operation.split(" ", 1)
        method, path = (parts[0].upper(), parts[1]) if len(parts) == 2 else ("POST", parts[0])
        if not path.startswith("/"): path = "/" + path
        
        # Replace path parameters
        for k, v in payload.items():
            if f"{{{k}}}" in path: path = path.replace(f"{{{k}}}", str(v))
            
        url = f"{base_url}{path}"
        if method == "GET":
            res = await client.get(url, headers=headers, params=payload)
        else:
            res = await client.request(method, url, headers=headers, json=payload)
        return res.json() if res.status_code < 400 else {"status": res.status_code, "error": res.text}

    @staticmethod
    async def _dispatch_stripe(client, config, operation, payload):
        key = config.get("stripe_secret_key")
        parts = operation.split(" ", 1)
        method, path = (parts[0].upper(), parts[1]) if len(parts) == 2 else ("POST", parts[0])
        if not path.startswith("/v1"): path = "/v1" + ("/" if not path.startswith("/") else "") + path
        url = f"https://api.stripe.com{path}"
        auth = (key, "")
        if method == "GET":
            res = await client.get(url, auth=auth, params=payload)
        else:
            res = await client.request(method, url, auth=auth, data=payload)
        return res.json()

    @staticmethod
    async def _dispatch_slack(client, config, operation, payload):
        token = config.get("slack_bot_token")
        parts = operation.split(" ", 1)
        method, path = (parts[0].upper(), parts[1]) if len(parts) == 2 else ("POST", parts[0])
        if not path.startswith("/api"): path = "/api" + ("/" if not path.startswith("/") else "") + path
        url = f"https://slack.com{path}"
        headers = {"Authorization": f"Bearer {token}"}
        if method == "GET":
            res = await client.get(url, headers=headers, params=payload)
        else:
            res = await client.request(method, url, headers=headers, json=payload)
        return res.json()
