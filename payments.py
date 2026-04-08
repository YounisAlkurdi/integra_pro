import stripe
import json
from fastapi import HTTPException, Request
from pydantic import BaseModel
from utils import get_env_safe

# Initialize Stripe Node
stripe.api_key = get_env_safe("STRIPE_SECRET_KEY")

# Pricing Protocols - Load once into Neural Cache
try:
    with open('pricing.json', 'r') as f:
        PRICING_DATA = json.load(f)
except Exception as e:
    PRICING_DATA = None
    print(f"=> ERROR: Pricing Protocal Cache Failure: {e}")

class PaymentRequest(BaseModel):
    payment_method_id: str
    amount: int
    plan_id: str
    billing_cycle: str

def validate_price(plan_id, cycle):
    """
    SECURITY GATE: Integrity Verification for Pricing.
    Prevents client-side price tampering.
    """
    if not PRICING_DATA:
        return -1
    try:
        plans = PRICING_DATA['pricing_data']['plans']
        plan = next((p for p in plans if p['id'] == plan_id), None)
        
        if not plan: return -1
        if plan[cycle]['price'] == 'Custom': return -1
        
        if cycle == 'monthly':
            return plan['monthly']['price'] * 100
        else:
            return plan['yearly']['price'] * 12 * 100 # Total for year
    except Exception:
        return -1

async def execute_payment(payment_req: PaymentRequest, request: Request):
    """
    Stripe Transaction Module.
    Executes the secure financial handshake with Stripe's cloud nodes.
    """
    expected_amount = validate_price(payment_req.plan_id, payment_req.billing_cycle)
    
    if expected_amount == -1:
        raise HTTPException(status_code=400, detail="Invalid Execution Node: Plan not found.")
    
    if payment_req.amount != expected_amount:
        client_ip = request.client.host
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
        raise HTTPException(status_code=500, detail="Internal Protocol Error")
