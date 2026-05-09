# Integra | Core Control Node
# Modular Architecture Loader

import sys, os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Fix: add both backend/ and the project root to Python path
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
current_dir = os.path.dirname(__file__)
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, root_dir)

# Load environment variables
env_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=env_path)

# --- 1. System Initialization ---
app = FastAPI(
    title="Integra | Core Control Node",
    description="Refactored Modular Forensic Backend",
    version="2.0.0"
)

# Global CORS Protocol
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500", "http://127.0.0.1:5500",
        "http://localhost:5501", "http://127.0.0.1:5501",
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8000", "http://127.0.0.1:8000",
        "https://integra-pro-puce.vercel.app",
        "https://integra-pro.vercel.app",
        "https://integra-ai.vercel.app",
        "null"
    ],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.middleware("http")
async def add_discovery_headers(request: Request, call_next):
    response = await call_next(request)
    base_url = str(request.base_url).rstrip('/')
    response.headers["Link"] = f'<{base_url}/.well-known/api-catalog.json>; rel="api-catalog"'
    return response

# --- 2. Route Registration (Modular) ---
from backend.routes import (
    user_routes,
    node_routes,
    log_routes,
    livekit_routes,
    agent_routes,
    gatekeeper_routes,
    behavioral_routes,
    nlp_routes,
    payment_routes,
    mail_routes,
    manager_routes,
    admin_routes
)

app.include_router(user_routes.router)
app.include_router(node_routes.router)
app.include_router(log_routes.router)
app.include_router(livekit_routes.router)
app.include_router(agent_routes.router)
app.include_router(gatekeeper_routes.router)
app.include_router(behavioral_routes.router)
app.include_router(nlp_routes.router)
app.include_router(payment_routes.router)
app.include_router(mail_routes.router)
app.include_router(manager_routes.router)
app.include_router(admin_routes.router)

# --- 3. System Health Node ---
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0-modular"}

@app.get("/")
async def sys_health():
    return {
        "status": "ONLINE",
        "system": "INTEGRA_CORE_V2",
        "architecture": "MODULAR_ROUTING",
        "neural_buffer": "SYNCED"
    }

if __name__ == "__main__":
    import uvicorn
    # In production, use environment variables for host/port
    uvicorn.run(app, host="0.0.0.0", port=8000)
