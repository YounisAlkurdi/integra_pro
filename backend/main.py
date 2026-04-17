import os
import logging
import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Core Imports
from .core.utils import get_env_safe
from .core.auth import get_current_user, get_user_profile_data, check_lockdown
from .core.supabase_client import get_supabase_client

# Route Imports
from .routes import nodes, agent_routes, livekit_routes, payments, system
from .core.rate_limit import standard_limit, strict_limit
from .services.mailer import Mailer

# Load environment
load_dotenv()

# Logger Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integra_core")

app = FastAPI(title="Integra | Core Control Node", version="1.1.0")

# --- Middlewares ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500", "http://127.0.0.1:5500",
        "http://localhost:5501", "http://127.0.0.1:5501",
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8000", "http://127.0.0.1:8000",
        "https://tist-integra.vercel.app" # Production Domain
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# --- Static Assets ---
os.makedirs("static/temp_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="Images"), name="images")
app.mount("/frames", StaticFiles(directory="frames"), name="frames")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# --- Routes Registration ---
from fastapi import Depends
app.include_router(nodes.router, prefix="/api", dependencies=[Depends(standard_limit), Depends(check_lockdown)])
app.include_router(agent_routes.router, prefix="/api", dependencies=[Depends(strict_limit), Depends(check_lockdown)])
app.include_router(livekit_routes.router, prefix="/api", dependencies=[Depends(standard_limit), Depends(check_lockdown)])
app.include_router(payments.router, prefix="/api", dependencies=[Depends(standard_limit)])
app.include_router(system.router, prefix="/api", dependencies=[Depends(standard_limit)])

# --- Root Endpoints ---

@app.get("/api/init", dependencies=[Depends(standard_limit)])
async def system_init(request: Request, user: dict = Depends(get_current_user)):
    """Unified SaaS Initialization Node. Reduces network RTT."""
    user_id = user.get("sub") or user.get("id") # Support both formats
    
    import asyncio
    from .routes.nodes import get_node_stats, get_active_streams
    
    profile_task = get_user_profile_data(user)
    stats_task = get_node_stats(user_id=user_id)
    nodes_task = get_active_streams(user_id=user_id)
    
    profile, stats, nodes_list = await asyncio.gather(profile_task, stats_task, nodes_task)
    
    return {
        "status": "READY",
        "profile": profile,
        "telemetry": stats,
        "active_nodes": nodes_list,
        "system_time": datetime.datetime.now().isoformat()
    }

# --- Compatibility Endpoints (Legacy Support) ---

@app.get("/api/user-profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return await get_user_profile_data(user)

@app.get("/api/stats")
async def sys_stats_legacy(user: dict = Depends(get_current_user)):
    from .routes.nodes import get_node_stats
    return await get_node_stats(user_id=user["sub"])

@app.post("/api/send-invitation")
async def send_invitation_legacy(request: Request, user: dict = Depends(get_current_user)):
    mailer = Mailer()
    data = await request.json()
    try:
        email = await mailer.send_interview_invitation(
            candidate_name=data.get("candidate_name"),
            candidate_email=data.get("candidate_email"),
            scheduled_at=data.get("scheduled_at"),
            room_link=data.get("room_link")
        )
        return {"status": "EMAIL_SENT", "id": email["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
async def get_config():
    """Client Configuration Distributor."""
    return {
        "stripePublishableKey": get_env_safe("STRIPE_PUBLISHABLE_KEY"),
        "livekitUrl": get_env_safe("LIVEKIT_URL")
    }

@app.get("/health")
async def sys_health():
    return {
        "status": "ONLINE",
        "system": "INTEGRA_CORE_SaaS_V1",
        "neural_buffer": "SYNCED"
    }

@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/index.html")

@app.get("/login")
async def login_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/login.html")

@app.get("/dashboard")
async def dashboard_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/dashboard.html")

@app.get("/appointments")
async def appointments_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/appointments.html")

@app.get("/audit")
async def audit_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/audit.html")

@app.get("/billing")
async def billing_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/billing.html")

@app.get("/checkout")
async def checkout_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/checkout.html")

@app.get("/integra-session")
async def session_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/integra-session.html")

@app.get("/llm-config")
async def llm_config_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/llm-config.html")

@app.get("/pricing")
async def pricing_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/pricing.html")

@app.get("/profile")
async def profile_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/profile.html")

@app.get("/reports")
async def reports_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/pages/reports.html")

import datetime

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
