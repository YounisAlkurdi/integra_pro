import stripe
import json
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from ..core.supabase_client import get_supabase_client
from ..core.auth import get_current_user
from ..core.utils import get_env_safe
from ..core.rate_limit import strict_limit, standard_limit
from ..core.audit import log_audit_event

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)

# Initialize Stripe
STRIPE_KEY = get_env_safe("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = get_env_safe("STRIPE_WEBHOOK_SECRET")
stripe.api_key = STRIPE_KEY

# Cache for pricing data
PRICING_DATA = None

def load_pricing():
    global PRICING_DATA
    try:
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        pricing_file = os.path.join(base_path, 'pricing.json')
        if os.path.exists(pricing_file):
            with open(pricing_file, 'r') as f:
                PRICING_DATA = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load pricing: {e}")

load_pricing()

class PaymentRequest(BaseModel):
    payment_method_id: str
    amount: int
    plan_id: str
    billing_cycle: str

def validate_price(plan_id: str, cycle: str) -> int:
    """Security Gate: Integrity Verification for Pricing."""
    if not PRICING_DATA:
        load_pricing()
    
    if not PRICING_DATA:
        return -1
        
    try:
        plans = PRICING_DATA.get('pricing_data', {}).get('plans', [])
        plan = next((p for p in plans if p['id'] == plan_id), None)
        
        if not plan: return -1
        
        price_str = plan.get(cycle, {}).get('price')
        if not price_str or str(price_str).lower() == 'custom': return -1
        
        base_price = int(price_str)
        if cycle == 'monthly':
            return base_price * 100
        else:
            return base_price * 12 * 100 # Yearly total
    except Exception:
        return -1

async def _sync_subscription_to_supabase(user_id: str, plan_id: str, cycle: str, customer_id: str = None):
    """Syncs subscription state to Supabase using the async client."""
    client = get_supabase_client()
    
    # Get plan limits
    limit_data = {"interviews_per_month": 5, "max_duration_mins": 10, "max_participants": 2}
    if PRICING_DATA:
        plans = PRICING_DATA.get('pricing_data', {}).get('plans', [])
        plan = next((p for p in plans if p['id'] == plan_id), None)
        if plan:
            limit_data = plan.get('limits', limit_data)

    data = {
        "user_id": user_id,
        "plan_id": plan_id,
        "billing_cycle": cycle,
        "stripe_customer_id": customer_id,
        "status": "ACTIVE",
        "interviews_limit": limit_data.get("interviews_per_month", 5),
        "max_duration_mins": limit_data.get("max_duration_mins", 10),
        "max_participants": limit_data.get("max_participants", 2)
    }
    
    # Upsert logic
    try:
        # Check if exists
        res = await client.from_("subscriptions").select("id").eq("user_id", user_id).execute()
        if res.data:
            await client.from_("subscriptions").update(data).eq("user_id", user_id).execute()
        else:
            await client.from_("subscriptions").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Supabase Subscription Sync Error: {e}")
        return False

async def _record_invoice(user_id: str, plan_id: str, amount: int, payment_intent_id: str):
    """Records the transaction in the ledger."""
    client = get_supabase_client()
    data = {
        "user_id": user_id,
        "plan_id": plan_id,
        "amount": amount,
        "payment_intent_id": payment_intent_id,
        "status": "PAID"
    }
    try:
        await client.from_("invoices").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Supabase Invoice Recording Error: {e}")
        return False

@router.post("/execute", dependencies=[Depends(strict_limit)])
async def execute_payment(payment_req: PaymentRequest, request: Request, user: dict = Depends(get_current_user)):
    """Stripe Transaction Module."""
    user_id = user["id"]
    expected_amount = validate_price(payment_req.plan_id, payment_req.billing_cycle)
    
    if expected_amount == -1:
        raise HTTPException(status_code=400, detail="Invalid Plan Configuration.")
    
    if payment_req.amount != expected_amount:
        # Log security threat
        ip_addr = request.client.host if request.client else "unknown"
        logger.warning(f"SECURITY: Price tampering attempt by {user_id} (IP: {ip_addr})")
        import asyncio
        asyncio.create_task(log_audit_event(
            user_id=user_id,
            action="SECURITY_THREAT",
            target_resource="payments",
            details={"type": "price_tampering", "expected": expected_amount, "received": payment_req.amount},
            ip_address=ip_addr
        ))
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
        
        # Immediate Sync
        customer_id = getattr(intent, 'customer', None)
        await _sync_subscription_to_supabase(user_id, payment_req.plan_id, payment_req.billing_cycle, customer_id)
        await _record_invoice(user_id, payment_req.plan_id, expected_amount, intent.id)
        
        import asyncio
        asyncio.create_task(log_audit_event(
            user_id=user_id,
            action="PAYMENT_EXECUTED",
            target_resource="stripe",
            details={"plan_id": payment_req.plan_id, "amount": expected_amount},
            ip_address=request.client.host if request.client else "unknown"
        ))
        
        return {"status": "success", "payment_intent_id": intent.id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Payment Execution Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Payment Processing Error")

@router.post("/webhook", dependencies=[Depends(standard_limit)])
async def stripe_webhook(request: Request):
    """Webhook Verification Node."""
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
            await _sync_subscription_to_supabase(user_id, plan_id, cycle, intent.get("customer"))
            await _record_invoice(user_id, plan_id, intent.get("amount"), intent.id)
            logger.info(f"STRIPE: Verified successful payment for {user_id}")

    return {"status": "event_processed"}
