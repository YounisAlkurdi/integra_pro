"""
Integra Neural Engine — Main Backend Entry Point
Architected for SaaS Scalability, Security, and Speed.
"""

import os
import time
import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from .utils import get_env_safe, cache
from .core.auth import get_current_user
from .engine import run_agent

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integra-engine")

app = FastAPI(
    title="Integra Neural Engine",
    description="Scalable SaaS Agentic Infrastructure",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static Files & Navigation ---
# Mount the frontend directory
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend"))
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    """Redirect to the dashboard or landing page."""
    return RedirectResponse(url="/static/index.html")

# --- Performance Middleware ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# --- Neural Engine Endpoints ---

@app.post("/api/v1/chat")
async def chat_endpoint(request: Request, user=Depends(get_current_user)):
    """
    Unified entry point for the Neural Agent.
    """
    body = await request.json()
    message = body.get("message")
    config = body.get("config", {})
    
    # Context Injection
    user_context = {
        "user_id": user["sub"],
        "email": user.get("email")
    }
    
    response = await run_agent(message, config, user_context)
    return {"status": "success", "response": response}

# --- Health Check ---
@app.get("/health")
async def health_check():
    return {"status": "operational", "timestamp": time.time()}

# --- Include Sub-Routers (Future Expansion) ---
# app.include_router(nodes.router, prefix="/api/v1/nodes", tags=["Nodes"])
# app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
