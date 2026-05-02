# Fix: add both backend/ and the project root to Python path
import sys, os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python" # Fix for Protobuf compatibility
current_dir = os.path.dirname(__file__)
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, root_dir)

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils import get_env_safe
from typing import Optional
from auth import get_current_user, get_user_profile_data, get_active_subscription, get_current_user_optional
from payments import PaymentRequest, execute_payment, handle_stripe_webhook
from nodes import NodeProtocol, create_neural_node, get_active_streams, get_node_stats
from logs import ChatLogEntry, save_chat_log, get_node_chat_logs
from mailer import send_interview_invitation
import livekit_routes
import agent_routes
import gatekeeper_routes
import behavioral_routes
import nlp_routes
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

# --- 1. System Initialization ---
app = FastAPI(title="Integra | Core Control Node")

class EmailRequest(BaseModel):
    candidate_name: str
    candidate_email: str
    scheduled_at: str
    room_link: str

# Global CORS Protocol
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500", "http://127.0.0.1:5500",
        "http://localhost:5501", "http://127.0.0.1:5501",
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8000", "http://127.0.0.1:8000",
        "null" # Support local file:// development
    ],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.middleware("http")
async def add_discovery_headers(request: Request, call_next):
    response = await call_next(request)
    # Advertise AI Agent Discovery Protocols dynamically based on host
    base_url = str(request.base_url).rstrip('/')
    response.headers["Link"] = f'<{base_url}/.well-known/api-catalog.json>; rel="api-catalog"'
    return response



# --- 2. Identity Endpoints (Supabase) ---
@app.get("/api/user-profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Identity Retrieval Node."""
    return get_user_profile_data(user)

# --- 3. Node & Stream Endpoints ---
@app.post("/api/nodes")
async def create_node(node: NodeProtocol, user: dict = Depends(get_current_user)):
    """Secure Node Initialization with Subscription Enforcement."""
    profile = get_user_profile_data(user)
    sub = profile.get("subscription") or {}
    limit = sub.get('interviews_limit', 5)
    
    # 1. Enforce limits from the subscription plan on the record
    node.max_participants = sub.get("max_participants", 2)
    node.max_duration_mins = sub.get("max_duration_mins", 10)
    
    # 2. Check Usage Limit
    stats = get_node_stats(user_id=user["sub"])
    if stats['total'] >= limit:
        raise HTTPException(status_code=402, detail="Neural Link Saturated: Limit Reached")
        
    return create_neural_node(node, user_id=user["sub"])

@app.get("/api/nodes")
async def list_nodes(user: dict = Depends(get_current_user)):
    """Data Stream Synchronization."""
    return get_active_streams(user_id=user["sub"])

@app.delete("/api/nodes/{room_id}")
async def remove_node(room_id: str, user: dict = Depends(get_current_user)):
    """Node Deletion Protocol."""
    from nodes import delete_node
    if delete_node(room_id):
        return {"status": "PURGED", "room_id": room_id}
    raise HTTPException(status_code=404, detail="Node not found")

@app.get("/api/stats")
async def sys_stats(user: dict = Depends(get_current_user)):
    """Telemetry Reporting Node."""
    return get_node_stats(user_id=user["sub"])

# --- 4. Chat Logging Endpoints ---
@app.post("/api/logs")
async def add_chat_log(log: ChatLogEntry, user: Optional[dict] = Depends(get_current_user_optional)):
    """Transcript Recording (Allowed for candidates in active sessions)."""
    user_id = user["sub"] if user else None
    return save_chat_log(log, user_id=user_id)

@app.get("/api/logs/{node_id}")
async def fetch_logs(node_id: str, user: dict = Depends(get_current_user)):
    """Transcript Retrieval Protocol."""
    return get_node_chat_logs(node_id, user_id=user["sub"])

# --- 4. LiveKit Endpoints (Token Generator) ---
# All logic lives in livekit_routes.py — same pattern as payments.py
app.include_router(livekit_routes.router)

# --- 5. Neural Agent Endpoints ---
app.include_router(agent_routes.router)

# --- 6. Gatekeeper Endpoints (Deepfake Verification) ---
app.include_router(gatekeeper_routes.router)

# --- 7. Behavioral Analysis (Gaze/WebSocket) ---
app.include_router(behavioral_routes.router)

# --- 8. NLP Forensic Engine ---
app.include_router(nlp_routes.router)

@app.get("/config")
async def get_config():
    """Stripe Config Distributor."""
    pk = get_env_safe("STRIPE_PUBLISHABLE_KEY")
    return {"publishableKey": pk}

@app.post("/create-payment-intent")
async def create_payment_intent(payment_req: PaymentRequest, request: Request, user: dict = Depends(get_current_user)):
    """Stripe Transaction Node."""
    return await execute_payment(payment_req, request, user["sub"])

@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Stripe Cloud Event Handshake."""
    return await handle_stripe_webhook(request)

# --- 6. System Health Node ---
@app.post("/api/send-invitation")
async def send_invitation(data: EmailRequest, user: dict = Depends(get_current_user)):
    """Automated Email Invitation via Gmail SMTP (Delegated to mailer.py)."""
    try:
        email = send_interview_invitation(
            candidate_name=data.candidate_name,
            candidate_email=data.candidate_email,
            scheduled_at=data.scheduled_at,
            room_link=data.room_link
        )
        return {"status": "EMAIL_SENT", "id": email["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def sys_health():
    return {
        "status": "ONLINE",
        "system": "INTEGRA_CORE_V1",
        "neural_buffer": "SYNCED"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
