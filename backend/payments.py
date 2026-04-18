import stripe
import json
import os
from fastapi import HTTPException, Request
from pydantic import BaseModel
from utils import get_env_safe

# Initialize Stripe Node
stripe.api_key = get_env_safe("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = get_env_safe("STRIPE_WEBHOOK_SECRET")

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

def _update_subscription_in_db(user_id, plan_id, cycle, customer_id=None):
    """Internal database update after payment confirmation."""
    import urllib.request
    
    # Reload pricing data dynamically to ensure latest limits
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        pricing_path = os.path.join(base_path, '..', 'data', 'pricing.json')
        with open(pricing_path, 'r') as f:
            neural_pricing = json.load(f)
    except Exception as e:
        print(f"=> ERROR: Failed to load pricing.json in _update_subscription_in_db: {e}")
        neural_pricing = PRICING_DATA

    # Use on_conflict=user_id for UPSERT logic (requires unique constraint on user_id)
    url = f"{SUPABASE_URL}/rest/v1/subscriptions?on_conflict=user_id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    # Default Limits
    limit_data = {"interviews_per_month": 5, "max_duration_mins": 10, "max_participants": 2}
    
    if neural_pricing:
        plans = neural_pricing.get('pricing_data', {}).get('plans', [])
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
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r: return True
    except Exception as e:
        print(f"FAILED TO UPSERT SUBSCRIPTION: {e}")
        return False

def _create_invoice_in_db(user_id, plan_id, amount, payment_intent_id):
    """Creates an invoice record in the ledger."""
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/invoices"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "user_id": user_id,
        "plan_id": plan_id,
        "amount": amount,
        "payment_intent_id": payment_intent_id,
        "status": "PAID"
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r: return True
    except Exception as e:
        print(f"FAILED TO CREATE INVOICE: {e}")
        return False

# Pricing Protocols - Load once into Neural Cache
try:
    base_path = os.path.dirname(os.path.abspath(__file__))
    pricing_path = os.path.join(base_path, '..', 'data', 'pricing.json')
    with open(pricing_path, 'r') as f:
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
        if str(plan[cycle]['price']).lower() == 'custom': return -1
        
        if cycle == 'monthly':
            return int(plan['monthly']['price']) * 100
        else:
            return int(plan['yearly']['price']) * 12 * 100 # Total for year
    except Exception:
        return -1

async def execute_payment(payment_req: PaymentRequest, request: Request, user_id: str):
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
        # In new structure, logs should probably go to a logs folder or handled by logs.py
        # For now, let's keep it in the root or backend? The doc says logs.py handles utilities.
        # Let's put security_threats.log in the root for now as it was there, or move to logs/
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'security_threats.log')
        with open(log_path, 'a') as log:
            log.write(f"PROXIED_THREAT: [Plan:{payment_req.plan_id}] [IP:{client_ip}] [Attempted:{payment_req.amount}] [Required:{expected_amount}]\n")
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
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "never"
            }
        )
        
        # PROACTIVE RECORDING: Link invoice immediately for synchronized feedback
        customer_id = getattr(intent, 'customer', None)
        _update_subscription_in_db(user_id, payment_req.plan_id, payment_req.billing_cycle, customer_id)
        _create_invoice_in_db(user_id, payment_req.plan_id, expected_amount, intent.id)
        
        return {"status": "success", "payment_intent_id": intent.id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"STT Transaction Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Protocol Error")

async def handle_stripe_webhook(request: Request):
    """
    Webhook Verification Node.
    Authenticates notifications from Stripe Cloud and updates subscriptions.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook Error: {str(e)}")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        metadata = intent.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_id = metadata.get("plan_id")
        cycle   = metadata.get("billing_cycle")

        if user_id and plan_id:
            # 1. Update Subscription Status
            _update_subscription_in_db(user_id, plan_id, cycle, intent.get("customer"))
            # 2. Record Invoice in Ledger
            _create_invoice_in_db(user_id, plan_id, intent.get("amount"), intent.id)
            print(f"STRIPE: Payment and Invoice confirmed for user {user_id}")

    return {"status": "event_processed"}
