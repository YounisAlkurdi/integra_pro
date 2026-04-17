import time
from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from .cache import integra_cache

class RateLimiter:
    """
    SaaS Rate Limiter — Hybrid Memory/Redis.
    Optimized for Integra's global command structure.
    """
    def __init__(self, requests: int, window: int, scope: str = "default"):
        self.requests = requests
        self.window = window
        self.scope = scope

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        cache_key = f"ratelimit:{self.scope}:{client_ip}"
        
        # Get history from cache
        history = integra_cache.get(cache_key) or []
        now = time.time()
        
        # Clean up old requests
        history = [req_time for req_time in history if now - req_time < self.window]
        
        if len(history) >= self.requests:
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests} requests per {self.window} seconds."
            )
            
        history.append(now)
        # Store back in cache with window as TTL
        integra_cache.set(cache_key, history, ttl=self.window)

# Standard limits
standard_limit = RateLimiter(requests=100, window=60, scope="std") # 100 requests per minute
strict_limit = RateLimiter(requests=20, window=60, scope="strict") # 20 requests per minute (e.g., LLM calls, payments)
