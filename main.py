import stripe
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import json

# Load env
load_dotenv()

# Secure Key Extraction & Sanitization
def get_env_safe(key: str):
    val = os.getenv(key)
    if not val: return ""
    return val.strip().replace('"', '').replace("'", "")

# Initialize
app = FastAPI()
stripe.api_key = get_env_safe("STRIPE_SECRET_KEY")

# 1. Performance Upgrade: Neural Cache
# Load Pricing Data once into RAM to reduce disk I/O
try:
    with open('pricing.json', 'r') as f:
        PRICING_DATA = json.load(f)
        print("=> SYSTEM: Pricing Protocols Loaded into Neural Space.")
except Exception as e:
    PRICING_DATA = None
    print(f"=> ERROR: Critical Cache Failure: {e}")

# CORS Policy => Global Access (Local Dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

import json

class PaymentRequest(BaseModel):
    payment_method_id: str
    amount: int
    plan_id: str
    billing_cycle: str

def validate_price(plan_id, cycle):
    if not PRICING_DATA: return -1
    try:
        plans = PRICING_DATA['pricing_data']['plans']
        plan = next((p for p in plans if p['id'] == plan_id), None)
        
        if not plan: return -1
        if plan[cycle]['price'] == 'Custom': return -1
        
        if cycle == 'monthly':
            return plan['monthly']['price'] * 100
        else:
            return plan['yearly']['price'] * 12 * 100 # Total for year
    except Exception as e:
        print(f"=> ERROR_NODE: {e}")
        return -1

@app.get("/config")
async def get_config():
    pk = get_env_safe("STRIPE_PUBLISHABLE_KEY")
    return {"publishableKey": pk}

@app.post("/create-payment-intent")
async def create_payment(payment_req: PaymentRequest, request: Request):
    expected_amount = validate_price(payment_req.plan_id, payment_req.billing_cycle)
    
    # SECURITY GATE: Integrity Verification
    if expected_amount == -1:
        raise HTTPException(status_code=400, detail="Invalid Execution Node: Plan not found.")
    
    if payment_req.amount != expected_amount:
        # LOGGING UPGRADE: Threat Identity Extraction
        client_ip = request.client.host
        print(f"!!! SECURITY ALERT / THREAT DETECTED !!!")
        print(f"-> Origin Node (IP): {client_ip}")
        print(f"-> Violation: Price tampering detected.")
        
        # PERSISTENT STORAGE: Secure Logging Protocol
        with open('security_threats.log', 'a') as log:
            log.write(f"PROXIED_THREAT: [Plan:{payment_req.plan_id}] [IP:{client_ip}] [Attempted:{payment_req.amount}] [Required:{expected_amount}]\n")

        raise HTTPException(status_code=403, detail="Security Violation: Price tampering detected.")

    try:
        intent = stripe.PaymentIntent.create(
            amount=expected_amount,
            currency="usd",
            payment_method=payment_req.payment_method_id,
            confirm=True,
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "never"
            }
        )
        return {"status": "success", "payment_intent_id": intent.id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"=> FATAL PROTOCOL ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Protocol Error")
