import stripe
import json
import os
from fastapi import HTTPException, Request
from pydantic import BaseModel
from ..utils import get_env_safe
from ..supabase_client import supabase

# Initialize Stripe Node
stripe.api_key = get_env_safe("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = get_env_safe("STRIPE_WEBHOOK_SECRET")

# Pricing Protocols - Load from root or fallback
PRICING_FILE = os.path.join(os.getcwd(), 'pricing.json')
try:
    with open(PRICING_FILE, 'r') as f:
        PRICING_DATA = json.load(f)
except Exception as e:
    PRICING_DATA = None
    print(f"=> ERROR: Pricing Protocol Cache Failure: {e}")

def _update_subscription_in_db(user_id, plan_id, cycle, customer_id=None):
    """Internal database update after payment confirmation."""
    global PRICING_DATA
    
    # Default Limits
    limit_data = {"interviews_per_month": 5, "max_duration_mins": 10, "max_participants": 2}
    
    if PRICING_DATA:
        plans = PRICING_DATA.get('pricing_data', {}).get('plans', [])
        plan = next((p for p in plans if p['id'] == plan_id), None)
        if plan:
            limit_data = plan.get('limits', limit_data)

    print(f"=> NEURAL_SYNC: Updating Subscription for {user_id} -> Plan: {plan_id} (Duration: {limit_data.get('max_duration_mins')}m)")

    body = {
        "user_id": user_id,
        "plan_id": plan_id,
        "billing_cycle": cycle or "monthly",
        "stripe_customer_id": customer_id,
        "status": "ACTIVE",
        "interviews_limit": limit_data.get("interviews_per_month", 5),
        "max_duration_mins": limit_data.get("max_duration_mins", 10),
        "max_participants": limit_data.get("max_participants", 2)
    }
    
    # Use modular upsert logic
    import asyncio
    # Since this might be called from a sync context or webhook, we might need a sync wrapper or just await it if async
    # For now, keeping it simple as this is mostly called from async execute_payment or handle_stripe_webhook
    return True # Placeholder for actual async call if needed, but better to keep it clean

async def _update_subscription_in_db_async(user_id, plan_id, cycle, customer_id=None):
    global PRICING_DATA
    limit_data = {"interviews_per_month": 5, "max_duration_mins": 10, "max_participants": 2}
    if PRICING_DATA:
        plans = PRICING_DATA.get('pricing_data', {}).get('plans', [])
        plan = next((p for p in plans if p['id'] == plan_id), None)
        if plan: limit_data = plan.get('limits', limit_data)

    body = {
        "user_id": user_id,
        "plan_id": plan_id,
        "billing_cycle": cycle or "monthly",
        "stripe_customer_id": customer_id,
        "status": "ACTIVE",
        "interviews_limit": limit_data.get("interviews_per_month", 5),
        "max_duration_mins": limit_data.get("max_duration_mins", 10),
        "max_participants": limit_data.get("max_participants", 2)
    }
    await supabase.upsert("subscriptions", body, on_conflict="user_id")
    return True

async def _create_invoice_in_db_async(user_id, plan_id, amount, payment_intent_id):
    body = {
        "user_id": user_id,
        "plan_id": plan_id,
        "amount": amount,
        "payment_intent_id": payment_intent_id,
        "status": "PAID"
    }
    await supabase.post("invoices", body)
    return True

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
        if str(plan[cycle]['price']).lower() == 'custom': return -1
        
        if cycle == 'monthly':
            return int(plan['monthly']['price']) * 100
        else:
            return int(plan['yearly']['price']) * 12 * 100
    except Exception:
        return -1

async def execute_payment(payment_req: PaymentRequest, request: Request, user_id: str):
    expected_amount = validate_price(payment_req.plan_id, payment_req.billing_cycle)
    if expected_amount == -1:
        raise HTTPException(status_code=400, detail="Invalid Execution Node: Plan not found.")
    
    if payment_req.amount != expected_amount:
        # Security logging
        log_path = os.path.join(os.getcwd(), 'security_threats.log')
        with open(log_path, 'a') as log:
            log.write(f"PROXIED_THREAT: [Plan:{payment_req.plan_id}] [IP:{request.client.host}] [Attempted:{payment_req.amount}] [Required:{expected_amount}]\n")
        raise HTTPException(status_code=403, detail="Security Violation: Price tampering detected.")

    try:
        intent = stripe.PaymentIntent.create(
            amount=expected_amount,
            currency="usd",
            payment_method=payment_req.payment_method_id,
            confirm=True,
            metadata={
                "user_id": user_id,
                "plan_id": payment_req.plan_id,
                "billing_cycle": payment_req.billing_cycle
            },
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"}
        )
        
        await _update_subscription_in_db_async(user_id, payment_req.plan_id, payment_req.billing_cycle, getattr(intent, 'customer', None))
        await _create_invoice_in_db_async(user_id, payment_req.plan_id, expected_amount, intent.id)
        
        return {"status": "success", "payment_intent_id": intent.id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"STT Transaction Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Protocol Error")

async def handle_stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook Error: {str(e)}")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        metadata = intent.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_id = metadata.get("plan_id")
        cycle = metadata.get("billing_cycle")

        if user_id and plan_id:
            await _update_subscription_in_db_async(user_id, plan_id, cycle, intent.get("customer"))
            await _create_invoice_in_db_async(user_id, plan_id, intent.get("amount"), intent.id)

    return {"status": "event_processed"}
