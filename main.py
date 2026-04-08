from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils import get_env_safe
from auth import get_current_user, get_user_profile_data
from payments import PaymentRequest, execute_payment
from nodes import NodeProtocol, create_neural_node, get_active_streams, get_node_stats
import livekit as livekit_module
import os
from dotenv import load_dotenv

load_dotenv()

# --- 1. System Initialization ---
app = FastAPI(title="Integra | Core Control Node")

# Global CORS Protocol
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500",
                   "http://localhost:5501", "http://127.0.0.1:5501"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

# --- 2. Identity Endpoints (Supabase) ---
@app.get("/api/user-profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Identity Retrieval Node."""
    return get_user_profile_data(user)

# --- 3. Node & Stream Endpoints ---
@app.post("/api/nodes")
async def create_node(node: NodeProtocol, user: dict = Depends(get_current_user)):
    """Secure Node Initialization."""
    return create_neural_node(node)

@app.get("/api/nodes")
async def list_nodes(user: dict = Depends(get_current_user)):
    """Data Stream Synchronization."""
    return get_active_streams()

@app.get("/api/stats")
async def sys_stats(user: dict = Depends(get_current_user)):
    """Telemetry Reporting Node."""
    return get_node_stats()

# --- 4. LiveKit Endpoints (Token Generator) ---
# All logic lives in livekit.py — same pattern as payments.py
app.include_router(livekit_module.router)

@app.get("/config")
async def get_config():
    """Stripe Config Distributor."""
    pk = get_env_safe("STRIPE_PUBLISHABLE_KEY")
    return {"publishableKey": pk}

@app.post("/create-payment-intent")
async def create_payment_intent(payment_req: PaymentRequest, request: Request):
    """Stripe Transaction Node."""
    return await execute_payment(payment_req, request)

# --- 6. System Health Node ---
@app.get("/")
async def sys_health():
    return {
        "status": "ONLINE",
        "system": "INTEGRA_CORE_V1",
        "neural_buffer": "SYNCED"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
