from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from utils import get_env_safe
from auth import get_current_user, get_user_profile_data
from payments import PaymentRequest, execute_payment
from nodes import NodeProtocol, create_neural_node, get_active_streams, get_node_stats

# --- 1. System Initialization ---
app = FastAPI(title="Integra | Core Control Node")

# Global CORS Protocol
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Identity Endpoints (Supabase) ---
@app.get("/api/user-profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Identity Retrieval Node.
    Returns the operator profile from the secure Supabase identity buffer.
    """
    return get_user_profile_data(user)

# --- 3. Node & Stream Endpoints ---
@app.post("/api/nodes")
async def create_node(node: NodeProtocol, user: dict = Depends(get_current_user)):
    """
    Secure Node Initialization.
    Requires an authenticated Command Operator to establish a new data stream.
    """
    return create_neural_node(node)

@app.get("/api/nodes")
async def list_nodes(user: dict = Depends(get_current_user)):
    """
    Data Stream Synchronization.
    Retrieves all active neural streams for the authenticated operator.
    """
    return get_active_streams()

@app.get("/api/stats")
async def sys_stats(user: dict = Depends(get_current_user)):
    """
    Telemetry Reporting Node.
    Returns real-time system performance and node metrics.
    """
    return get_node_stats()

# --- 4. Financial Endpoints (Stripe Card) ---
@app.get("/config")
async def get_config():
    """
    Stripe Config Distributor.
    Distributes the publishable protocol key to frontend nodes.
    """
    pk = get_env_safe("STRIPE_PUBLISHABLE_KEY")
    return {"publishableKey": pk}

@app.post("/create-payment-intent")
async def create_payment_intent(payment_req: PaymentRequest, request: Request):
    """
    Stripe Transaction Node.
    Executes a secure financial handshake through the Payments Module.
    """
    return await execute_payment(payment_req, request)

# --- 4. System Health Node ---
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
